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
ORDERS_FILE = Path(__file__).parent / "data" / "orders.json"

def load_users() -> list[dict]:
    with open(DATA_FILE) as file:
        return json.load(file)["users"]

def load_orders() -> list[dict]:
    with open(ORDERS_FILE) as file:
        return json.load(file)["orders"]

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

ROLE_LEVELS = {"user": 1, "admin": 2, "bigadmin": 3}
# role hierarchy: bigadmin outranks admin outranks user

def role_required(minimum_role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if ROLE_LEVELS.get(session.get("role"), 0) < ROLE_LEVELS[minimum_role]:
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
                session["id"] = user["id"]
                session["username"] = user["username"]
                session["role"] = user["role"]
                return redirect(url_for("dashboard"))
        
        error = "Invalid username or password"
    return render_template("login.html", error=error)

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

# --------------------
# Dashboard Routes
# --------------------

@app.route("/dashboard")
@login_required
def dashboard():
    if session["role"] in ("admin", "bigadmin"):
        return redirect(url_for("dashboard_admin"))
    if session["role"] == "user":
        return redirect(url_for("dashboard_users"))
    
    # don't know the role
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard/users")
@login_required
@role_required("user")
def dashboard_users():
    my_orders = [o for o in load_orders() if o["user_id"] == session["id"]]
    return render_template(
        "user_dashboard.html",
        username=session["username"],
        role_name=session["role"],
        userid=session["id"],
        orders=my_orders,
    )

@app.route("/dashboard/admin")
@login_required
@role_required("admin")
def dashboard_admin():
    # sample tickets until the real ticket system exists
    tickets = [
        {"id": 88, "operator_id": 2, "body": "the van is making the weird noise again. also I ate the evidence (it was a cherry)"},
        {"id": 89, "operator_id": 3, "body": "skinny pete here. lost another shipment. do NOT tell the boss. update: the boss knows."},
        {"id": 90, "operator_id": 1, "body": "when do I get good clearance? the plans page just says 403 for me."},
    ]
    return render_template(
        "admin_dashboard.html",
        username=session["username"],
        role_name=session["role"],
        userid=session["id"],
        users=load_users(),
        tickets=tickets,
    )

# --------------------
# Entry Point
# --------------------

if __name__ == "__main__":
    app.run(debug=True)