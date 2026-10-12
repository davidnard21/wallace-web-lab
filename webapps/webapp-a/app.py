from flask import Flask, render_template, request, session, redirect, url_for
import json
from pathlib import Path
from functools import wraps

app = Flask(__name__)
app.secret_key = "lab-demo-secret"
# init the flask app

def role_required(role):
    @wraps(role)
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "username" not in session:
                return redirect(url_for("login"))
            if session.get("role") != role:
                return redirect(url_for("dashboard"))  # or abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
# ngl I copied and pasted this from google but it is necessary to make sure that people dont just
# type in /dashboard/users or /admin and get it without login

DATA_FILE = Path(__file__).parent / "data" / "users.json"
# set the file path for the users.json

def get_users():
# load the json data
    with open(DATA_FILE,"r") as file:
        data = json.load(file)
    return data["users"]

@app.route("/")
def home():
    return render_template("index.html")
    # sets what html file gets loaded for the root dir

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        # make sure user is authenticated
        return redirect(url_for("login"))

    current_username = session["username"]
    current_role = session["role"]
    # Establish role/username from login page entry

    if current_role == "admin":
        return redirect(url_for("dash_admin"))
        # if they are authenticated, load the dashboard and pass the user and role
    elif current_role == "user":
        return redirect(url_for("dash_users"))
    
    return redirect(url_for("login"))

@app.route("/dashboard/users")
@role_required("user")
def dash_users():
    return render_template("user_dashboard.html", username=session["username"])

@app.route("/dashboard/admin")
@role_required("admin")
def dash_admin():
    return render_template("admin_dashboard.html", username=session["username"])

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        for user in get_users():
            # is that username and password in users.json?
            if (user["username"] == username and user["password"] == password):
                session["username"] = user["username"]
                session["role"] = user["role"]

                return redirect(url_for("dashboard"))
                # if it matches, send to dashboard

        return render_template("login.html", error="invalid username or password")
        # if it don't match, deny

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    # wipes everything

    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
