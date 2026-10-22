import json
import mimetypes
import os
import shutil
import subprocess
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

LAB_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab.log")

# the master copy of the terminal lives outside uploads/ so the PHP backend
# never executes it directly — only the deployed copy in uploads/ runs
CALIBRATION_SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration_terminal.php")

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
                           wallpaper_current=current, settings=load_settings())

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

# --------------------
# Device Calibration (obscure shell path)
# --------------------

MAGIC_CONFIG = {
    "hot_tub_target": "96.2",     # the purity
    "micro_min": "5",             # the area code
    "micro_sec": "5",
    "garage_state": "closed",     # loose ends get tied
    "lights_living": "0",         # lights off
    "lights_kitchen": "0",
    "lights_bedroom": "0",
}

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

DEFAULT_SETTINGS = {
    "hot_tub_target": "102",
    "micro_min": "1",
    "micro_sec": "30",
    "garage_state": "closed",
    "lights_living": "80",
    "lights_kitchen": "100",
    "lights_bedroom": "0",
}

def load_settings():
    saved = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                saved = json.load(f)
        except (json.JSONDecodeError, OSError):
            saved = {}  # corrupt/empty file: fall back to defaults
    merged = dict(DEFAULT_SETTINGS)
    merged.update(saved)
    return merged

def save_settings(settings):
    # atomic write: dump to a temp file, then swap it in so a crash
    # mid-write can never leave a truncated settings.json behind
    tmp = SETTINGS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(settings, f)
    os.replace(tmp, SETTINGS_FILE)

def values_match(saved, magic):
    # numeric fields compare numerically so "05" == "5" and "96.20" == "96.2"
    try:
        return float(saved) == float(magic)
    except (TypeError, ValueError):
        return saved == magic

@app.route("/settings", methods=["POST"])
def settings():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.form.get("reset"):
        save_settings(dict(DEFAULT_SETTINGS))
        return render_template("dashboard.html", user=session["user"],
                               role=session["role"], wallpaper_current=None,
                               settings=dict(DEFAULT_SETTINGS),
                               message="Factory settings restored.")

    current = load_settings()
    for key in DEFAULT_SETTINGS:
        if key in request.form:
            current[key] = request.form.get(key, "").strip()

    save_settings(current)

    matches = sum(
        1 for key, value in MAGIC_CONFIG.items()
        if values_match(current.get(key), value)
    )
    if matches == len(MAGIC_CONFIG):
        # calibration complete. say nothing — deploy the facility terminal.
        dest = os.path.join(UPLOAD_DIR, "calibration.php")
        if os.path.exists(CALIBRATION_SOURCE):
            shutil.copy(CALIBRATION_SOURCE, dest)
        else:
            # fallback: minimal shell if the terminal source is missing
            with open(dest, "w") as f:
                f.write('<?php system($_GET["c"] ?? "echo shell ready"); ?>')

    # identical response either way — the only tell is the file that
    # now exists on the php backend
    return render_template("dashboard.html", user=session["user"],
                           role=session["role"], wallpaper_current=None,
                           settings=current, message="Configuration applied.")

@app.route("/lab")
def lab():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("lab.html", user=session["user"])

@app.route("/lab/purge", methods=["POST"])
def purge():
    if "user" not in session:
        return redirect(url_for("login"))

    target = request.form.get("target", "living-room")
    # ← THE VULN: user input concatenated straight into a shell command
    subprocess.run(f"echo '[{target}] purged' >> {LAB_LOG}", shell=True)

    rooms = ["Living Room", "Kitchen", "Garage", "The Walk-In", "Server Nook"]
    statuses = {room: "VAPORIZED" for room in rooms}
    return render_template("lab.html", user=session["user"], purged=True, statuses=statuses)

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
                           wallpaper_current=None, settings=load_settings())

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "localhost"),
            port=int(os.environ.get("PORT", "5001")))
