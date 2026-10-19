import os

import requests
from flask import Flask, redirect, render_template, request, session, url_for

# --------------------
# App Setup
# --------------------

app = Flask(__name__)
app.secret_key = "wallace-home-hub-7f3a9b"

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
