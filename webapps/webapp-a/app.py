from flask import Flask, render_template, request, session, redirect, url_for
import json
from pathlib import Path

app = Flask(__name__)
app.secret_key = "lab-demo-secret"
# init the flask app

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
        return render_template("admin_dashboard.html", username=current_username, role=current_role)
        # if they are authenticated, load the dashboard and pass the user and role
    elif current_role == "user":
        return render_template("user_dashboard.html", username=current_username, role=current_role)
    elif current_role == "guest":
        return render_template("guest_dashboard.html", username=current_username, role=current_role)
    
    return redirect(url_for("login"))

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

if __name__ == "__main__":
    app.run(debug=True)
