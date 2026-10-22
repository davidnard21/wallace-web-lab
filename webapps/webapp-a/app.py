from functools import wraps
from pathlib import Path
import base64
import json
import os

from flask import Flask, abort, g, redirect, render_template, request, send_from_directory, url_for

# --------------------
# App Setup
# --------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lab-demo-secret")
# the XSS chain needs document.cookie to be readable by scripts
app.config["SESSION_COOKIE_HTTPONLY"] = False

DATA_FILE = Path(__file__).parent / "data" / "users.json"
ORDERS_FILE = Path(__file__).parent / "data" / "orders.json"
TICKETS_FILE = Path(__file__).parent / "data" / "tickets.json"
COLLECTED_FILE = Path(__file__).parent / "data" / "collected.log"

def load_users() -> list[dict]:
    with open(DATA_FILE) as file:
        return json.load(file)["users"]

def save_users(users: list[dict]):
    with open(DATA_FILE, "w") as file:
        json.dump({"users": users}, file, indent=4)

def load_orders() -> list[dict]:
    with open(ORDERS_FILE) as file:
        return json.load(file)["orders"]

def load_tickets() -> list[dict]:
    with open(TICKETS_FILE) as file:
        return json.load(file)["tickets"]

def save_tickets(tickets: list[dict]):
    with open(TICKETS_FILE, "w") as file:
        json.dump({"tickets": tickets}, file, indent=4)

# --------------------
# Auth
# --------------------
# "legacy" auth scheme: the ONLY credential is a cookie holding
# base64(username:password). the server decodes it and looks the pair up in
# users.json on every request. any XSS can read it, and it decodes to exactly
# what it looks like.

def current_user() -> dict | None:
    if "user" in g:
        return g.user
    g.user = None
    raw = request.cookies.get("operator_token")
    if raw:
        try:
            username, _, password = base64.b64decode(raw).decode().partition(":")
            g.user = next(
                (u for u in load_users() if u["username"] == username and u["password"] == password),
                None,
            )
        except Exception:
            g.user = None
    return g.user

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

ROLE_LEVELS = {"user": 1, "admin": 2, "bigadmin": 3}
# role hierarchy: bigadmin outranks admin outranks user

def role_required(minimum_role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None or ROLE_LEVELS.get(user["role"], 0) < ROLE_LEVELS[minimum_role]:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def grant_operator_cookie(response, user):
    token = base64.b64encode(f"{user['username']}:{user['password']}".encode()).decode()
    response.set_cookie("operator_token", token)
    return response

# --------------------
# Public Routes
# --------------------

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/robots.txt")
def robots():
    body = "User-agent: *\nDisallow: /register\nDisallow: /plans\nDisallow: /admin1/"
    return app.response_class(body, mimetype="text/plain")

# --------------------
# Auth Routes
# --------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        for user in load_users():
            if user["username"] == username and user["password"] == password:
                response = app.make_response(redirect(url_for("dashboard")))
                return grant_operator_cookie(response, user)

        error = "Invalid username or password"
        response = app.make_response(render_template("login.html", error=error))
        # "password reset infrastructure" — never rendered by the browser,
        # only visible in an intercepting proxy (Burp) or curl -v
        if username == "admin":
            response.headers["X-Reset-Token"] = "bGlsLWxpemFyZC0xMjMh"
        return response
    return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "All fields required"
        elif any(u["username"] == username for u in load_users()):
            error = "That operator name is taken"
        else:
            users = load_users()
            users.append({
                "id": max(u["id"] for u in users) + 1,
                "username": username,
                "password": password,
                "role": "user",  # role is decided by the server, never the form
            })
            save_users(users)
            response = app.make_response(redirect(url_for("dashboard_users")))
            return grant_operator_cookie(response, users[-1])

    return render_template("register.html", error=error)

@app.route("/logout", methods=["GET", "POST"])
def logout():
    response = app.make_response(redirect(url_for("login")))
    response.delete_cookie("operator_token")
    return response

# --------------------
# Backup Portal (breadcrumb)
# --------------------

BACKUP_DIR = Path(__file__).parent / "static" / "admin1" / "thickbox" / "zips" / "seed" / "_dummy" / "backup"

# intermediate "directories" along the admin1 path get a real page so
# directory fuzzers see 200 and keep recursing deeper
ADMIN1_INTERMEDIATE_PATHS = {
    "",
    "thickbox",
    "thickbox/zips",
    "thickbox/zips/seed",
    "thickbox/zips/seed/_dummy",
    "thickbox/zips/seed/_dummy/backup",
}

@app.route("/admin1")
@app.route("/admin1/")
@app.route("/admin1/<path:subpath>")
def admin1_gate(subpath=None):
    if subpath is None or subpath.rstrip("/") in ADMIN1_INTERMEDIATE_PATHS:
        return app.response_class("almost there...\n", mimetype="text/plain")
    # unknown deeper paths: 403 looks like a permissions wall, 404 like the
    # path ends here — either way the real payload routes below still resolve
    return app.response_class("403 Forbidden — clearance insufficient\n", status=403, mimetype="text/plain")

@app.route("/admin1/thickbox/zips/seed/_dummy/backup/<path:filename>")
def backup_portal(filename):
    # legacy "backup portal" — the lizard photo's EXIF has the admin creds
    return send_from_directory(BACKUP_DIR, filename)

# --------------------
# Log Server (breadcrumbs)
# --------------------

LOGS_DIR = Path(__file__).parent / "data" / "logs"

@app.route("/logs")
@login_required
@role_required("admin")
def logs():
    # the internal log server — the pcap in here has the admin creds
    log_file = LOGS_DIR / "access.log"
    entries = log_file.read_text() if log_file.exists() else "log file empty"
    return render_template("logs.html", username=current_user()["username"], entries=entries)

@app.route("/download/<path:filename>")
@login_required
def download(filename):
    # BUG: the archive PAGE is management-only, but whoever wrote this route
    # forgot that the file itself should be too. any logged-in operator can
    # hit the direct link.
    return send_from_directory(LOGS_DIR, filename, as_attachment=True)

@app.route("/collect")
def collect():
    # "log service" sink — accepts anything, stores it. no auth: the victim's
    # browser hits this directly, and it doubles as the XSS exfil endpoint.
    data = request.args.get("c", "(empty)")
    with open(COLLECTED_FILE, "a") as f:
        f.write(request.headers.get("User-Agent", "?") + "\n")
        f.write(data + "\n\n")
    return "logged", 200

@app.route("/collected")
@login_required
def collected():
    entries = COLLECTED_FILE.read_text() if COLLECTED_FILE.exists() else "nothing collected yet"
    return render_template("collected.html", username=current_user()["username"], entries=entries)

# --------------------
# Dashboard Routes
# --------------------

@app.route("/dashboard")
@login_required
def dashboard():
    role = current_user()["role"]
    if role in ("admin", "bigadmin"):
        return redirect(url_for("dashboard_admin"))
    return redirect(url_for("dashboard_users"))

@app.route("/dashboard/users")
@login_required
@role_required("user")
def dashboard_users():
    me_user = current_user()
    # staff directory lookup — ?user_id=N shows another operator's profile
    requested_id = request.args.get("user_id", type=int)
    if requested_id is None:
        # always show the id in the url so players learn it's a parameter
        return redirect(url_for("dashboard_users", user_id=me_user["id"]))
    view_id = requested_id

    me = next((u for u in load_users() if u["id"] == view_id), None)
    if me is None:
        abort(404)
    if me["role"] in ("admin", "bigadmin"):
        # management profiles are not viewable at street-level clearance
        abort(403)

    orders = [o for o in load_orders() if o["user_id"] == view_id]
    return render_template(
        "user_dashboard.html",
        username=me_user["username"],
        role_name=me_user["role"],
        userid=view_id,
        orders=orders,
        display_name=me.get("display_name") or me.get("username"),
        fav_product=me.get("fav_product"),
        viewing_note=me.get("note"),
        viewing_other=(view_id != me_user["id"]),
        viewing_id=view_id,
    )

@app.route("/user/tickets", methods=["GET", "POST"])
@login_required
def submit_ticket():
    # browsers land here via GET after a submit (refresh/back) — just bounce home
    if request.method == "GET":
        return redirect(url_for("dashboard_users"))

    body = request.form.get("ticket", "").strip()
    if not body:
        return redirect(url_for("dashboard_users"))

    tickets = load_tickets()
    tickets.append({
        "id": max(t["id"] for t in tickets) + 1,
        "operator_id": current_user()["id"],
        "body": body,  # stored raw — no sanitization
    })
    save_tickets(tickets)
    return redirect(url_for("dashboard_users"))

@app.route("/user/profile", methods=["GET", "POST"])
@login_required
def update_profile():
    # browsers land here via GET after a submit (refresh/back) — just bounce home
    if request.method == "GET":
        return redirect(url_for("dashboard_users"))

    users = load_users()
    for user in users:
        if user["id"] == current_user()["id"]:
            user["display_name"] = request.form.get("display_name")
            user["fav_product"] = request.form.get("fav_product")
            user["role"] = request.form.get("role", "user")  # ← trusts the form
            break
    save_users(users)

    # role is re-read from users.json on the next request — promotes them immediately
    return redirect(url_for("dashboard"))

@app.route("/plans")
@login_required
@role_required("admin")
def plans():
    return render_template("plans.html")

@app.route("/secret-cherry-formula")
@login_required
@role_required("bigadmin")
def secret():
    return render_template("secret_cherry.html")

@app.route("/dashboard/admin/admintools")
@login_required
@role_required("admin")
def admintools():
    me_user = current_user()
    return render_template(
        "admintools.html",
        username=me_user["username"],
        role_name=me_user["role"],
        users=load_users(),
    )

@app.route("/dashboard/admin/admintools/reset/<int:user_id>", methods=["POST"])
@login_required
@role_required("admin")
def reset_password(user_id: int):
    new_password = request.form.get("password", "")
    if new_password:
        users = load_users()
        for user in users:
            if user["id"] == user_id:
                if user["role"] == "bigadmin":
                    # management credentials cannot be changed from the web UI.
                    # admins must use the /api/admin/reset integration instead.
                    abort(403)
                user["password"] = new_password
                break
        save_users(users)
    return redirect(url_for("admintools"))

@app.route("/api/admin/reset", methods=["POST"])
@login_required
@role_required("admin")
def api_admin_reset():
    """Privileged password-reset integration for the management account.

    Only reachable via an authenticated POST as an 'admin' (or bigadmin)
    user. Accepts JSON or form data:

        {"username": "daddylizard", "new_password": "..."}

    Returns JSON so it is meant to be called with curl/fetch, not from the
    admin tools UI.
    """
    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    new_password = data.get("new_password") or ""

    if not username or not new_password:
        return {"error": "username and new_password are required"}, 400

    # this endpoint exists to rotate the boss's credentials
    if username != "daddylizard":
        return {"error": "only the management account may be reset via this endpoint"}, 400

    users = load_users()
    for user in users:
        if user["username"] == username:
            user["password"] = new_password
            save_users(users)
            return {"status": "ok", "username": username, "message": "password updated"}

    return {"error": "unknown user"}, 404

@app.route("/dashboard/admin")
@login_required
@role_required("admin")
def dashboard_admin():
    me_user = current_user()
    return render_template(
        "admin_dashboard.html",
        username=me_user["username"],
        role_name=me_user["role"],
        userid=me_user["id"],
        users=load_users(),
        tickets=load_tickets(),
    )

# --------------------
# Entry Point
# --------------------

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "localhost"),
            port=int(os.environ.get("PORT", "5000")),
            debug=False)
