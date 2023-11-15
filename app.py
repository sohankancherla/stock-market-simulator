import os
from config import API_KEY
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
import re
import requests
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, lookup, usd

# Replace API_KEY with your own API key
api_key=API_KEY

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    return apology("TODO")


@app.route("/search", methods=["GET"])
@login_required
def buy():
    """Search for stock"""
    stock = request.args.get("q")
    if stock != None:
        if stock.strip():
            url = f"https://finnhub.io/api/v1/search?q={stock}&token={api_key}"
            response = requests.get(url)
            data = response.json()

            if response.status_code == 200 and data["result"]:
                result = []
                data = data["result"]
                for i in data:
                    symbol = i.get('symbol')
                    name = i.get("description")
                    if "." not in symbol:
                        stock_info = lookup(symbol, name)
                        if stock_info:
                            result.append(stock_info)
                                
                if not result:
                    flash("No results found.", "danger")
                    return render_template('search.html', search=stock)
                else:
                    return render_template('search.html', result=result, search=stock)
            else:
                flash("Error retrieving data.", "danger")
                return render_template('search.html', search=stock)
        else:
            flash("Please enter a symbol or company name.", "danger")
            return render_template('search.html', search=stock)
    else:
        return render_template('search.html', search="")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Make sure username has enough characters
        if len(username) < 3:
            flash("Usernames have at least 3 characters.", "danger")
            return render_template('login.html', username=username, password=password)

        # Make sure the username has valid characters
        if not re.match("^[\w.]+$", username):
            flash("Usernames only use letters, numbers, underscores and periods.", "danger")
            return render_template('login.html', username=username, password=password)

        # Make sure the password has enough characters
        if len(password) < 5:
            flash("Password have at least 5 characters.", "danger")
            return render_template('login.html', username=username, password=password)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Invalid username and/or password.", "danger")
            return render_template('login.html', username=username, password=password)


        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Make sure username has enough characters
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "danger")
            return render_template('register.html', username=username, password=password, confirmation=confirmation)

        # Make sure the username has valid characters
        if not re.match("^[\w.]+$", username):
            flash("Usernames can only use letters, numbers, underscores and periods.", "danger")
            return render_template('register.html', username=username, password=password, confirmation=confirmation)

        # Make sure the username is not taken
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if len(rows) != 0:
            flash("This username isn't available. Please try another.", "danger")
            return render_template('register.html', username=username, password=password, confirmation=confirmation)
        
        # Make sure the password has enough characters
        if len(password) < 5:
            flash("Password must be at least 5 characters.", "danger")
            return render_template('register.html', username=username, password=password, confirmation=confirmation)

        # Make sure the password matches the confirm password
        if password != confirmation:
            flash("The passwords you entered do not match.", "danger")
            return render_template('register.html', username=username, password=password, confirmation=confirmation)

        # All criteria are met, Add user to the database
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, generate_password_hash(password))
        return redirect("/")

    return render_template('register.html', username='', password='', confirmation='')


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    return apology("TODO")