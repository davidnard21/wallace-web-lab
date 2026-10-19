import mimetypes
import os

import uuid

import requests
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

# HomeHub does not keep its own accounts — it defers authentication to the
# operator portal (webapp-a) on every sign-in attempt. whatever creds are
# valid THERE for daddylizard are valid HERE, every single time.
OPERATOR_PORTAL = os.environ.get("OPERATOR_PORTAL_URL", "http://localhost:5000/login")
HUB_OPERATOR = "daddylizard"  # the boss's smart home, the boss's login

# --------------------
# Auth
# --------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        # ask the operator portal to validate the credentials
        try:
            check = requests.post(
                OPERATOR_PORTAL,
                data={"username": username, "password": password},
                allow_redirects=False,
                timeout=5,
            )
            portal_ok = check.status_code in (301, 302, 303)  # portal redirects on success
        except requests.RequestException:
            portal_ok = False

        if portal_ok and username == HUB_OPERATOR:
            session["user"] = username
            session["role"] = "superadmin"
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
    return render_template("dashboard.html", user=session["user"], role=session["role"])

if __name__ == "__main__":
    app.run(host="localhost", port=5001)
