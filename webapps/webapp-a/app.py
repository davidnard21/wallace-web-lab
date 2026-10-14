from functools import wraps
from pathlib import Path
import json
import os

from flask import Flask, abort, redirect, render_template, request, session, url_for

# --------------------
# App Setup
# --------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lab-demo-secret")

DATA_FILE = Path(__file__).parent / "data" / "users.json"

def load_users() -> list[dict]:
    with open(DATA_FILE) as file:
        return json.load(file)["users"]

# --------------------
# Auth Decorators
# --------------------

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def role_required(role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# --------------------
# Public Routes
# --------------------

@app.route("/")
def home():
    return render_template("index.html")

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
                session["username"] = user["username"]
                session["role"] = user["role"]
                return redirect(url_for("dashboard"))
        
        error = "Invalid username or password"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --------------------
# Dashboard Routes
# --------------------

@app.route("/dashboard")
@login_required
def dashboard():
    if session["role"] == "admin":
        return render_template("admin_dashboard.html")
    if session["role"] == "user":
        return render_template("user_dashboard.html")
    
    # don't know the role
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard/users")
@login_required
@role_required("admin")
def dashboard_users():
    return render_template("dashboard_users.html", username=session["username"])

@app.route("/dashboard/admin")
@login_required
@role_required("admin")
def dashboard_admin():
    return render_template("dashboard_admin.html", username=session["username"])

# --------------------
# Entry Point
# --------------------

if __name__ == "__main__":
    app.run(debug=True)