import json
import mimetypes
import os
import uuid
from pathlib import Path

from flask import (Flask, redirect, render_template, request, send_from_directory,
                   session, url_for)

# --------------------
# App Setup
# --------------------

app = Flask(__name__)
app.secret_key = "wallace-home-hub-7f3a9b"

# TV wallpaper uploads
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# HomeHub does not keep its own accounts — it authenticates against the
# same users.json that the operator portal (webapp-a) uses. Only the
# daddylizard account is allowed into the dashboard.
WEBAPP_A_USERS = Path(__file__).parent.parent / "webapp-a" / "data" / "users.json"
HUB_OPERATOR = "daddylizard"  # the boss's smart home, the boss's login


def validate_credentials(username: str, password: str) -> bool:
    with open(WEBAPP_A_USERS) as f:
        users = json.load(f)["users"]
    return any(
        u["username"] == username and u["password"] == password
        for u in users
    )

# --------------------
# Auth
# --------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if validate_credentials(username, password) and username == HUB_OPERATOR:
            session["user"] = username
            session["role"] = "bigadmin"  # daddylizard's role in users.json
            return redirect(url_for("dashboard"))

        error = "Access denied"

    return render_template("login.html", error=error)

@app.route("/tv/wallpaper", methods=["GET", "POST"])
def tv_wallpaper():
    if "user" not in session:
        return redirect(url_for("login"))

    message = None
    current = None

    if request.method == "POST":
        file = request.files.get("wallpaper")
        if file and file.filename:
            # "trust" the client-supplied filename — this is the attack surface
            name = file.filename.replace("\\", "/").split("/")[-1] or "wallpaper"
            file.save(os.path.join(UPLOAD_DIR, name))
            message = f"Wallpaper '{name}' applied to TV."
            current = name
        else:
            message = "No file selected."

    return render_template("dashboard.html", user=session["user"],
                           role=session["role"], wallpaper_message=message,
                           wallpaper_current=current)

@app.route("/tv/wallpaper/<path:filename>")
def tv_wallpaper_file(filename):
    if "user" not in session:
        return redirect(url_for("login"))
    # no extension/type validation — serves whatever was uploaded.
    # unknown types default to text/html so they render (and execute)
    # in the browser instead of downloading.
    mimetype, _ = mimetypes.guess_type(filename)
    return send_from_directory(
        UPLOAD_DIR,
        filename,
        mimetype=mimetype or "text/html",
        as_attachment=False,
    )

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

# --------------------
# Platform
# --------------------

@app.route("/")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["user"], role=session["role"],
                           wallpaper_current=None)

if __name__ == "__main__":
    app.run(host="localhost", port=5001)
