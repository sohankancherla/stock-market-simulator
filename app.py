import os
from config import API_KEY
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
import re
import requests
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, lookup, usd, current_time

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
    result = db.execute("SELECT symbol, name, shares, price FROM users JOIN portfolio ON user_id WHERE id = ?", session["user_id"])
    balance = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
    total = balance
    for stock in result:
        stock_info = None
        while stock_info == None:
            stock_info = lookup(stock["symbol"], stock["name"])
        stock["current_price"] = stock_info["price"]
        total += (stock_info["price"] * stock["shares"])
        stock["change"] = stock_info["change"]
    return render_template("portfolio.html", result=result, balance=balance, total=total)


@app.route("/search", methods=["GET"])
@login_required
def search():
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
    result = db.execute("SELECT symbol, name, shares, price, time FROM users JOIN history ON user_id WHERE id = ?", session["user_id"])
    return render_template("history.html", result=result)


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

@app.route("/buy", methods=["POST"])
@login_required
def buy():
    """buy shares of stock"""
    symbol = request.form.get("symbol")
    name = request.form.get("name")
    shares = request.form.get("shares")
    stock_info = lookup(symbol, name)
    if stock_info == None:
        flash("Unable to purchase.", "danger")
        return redirect("/")
    else:
        price = stock_info["price"]
        balance = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
        if (float(shares) * float(price)) > balance:
            flash("Not enough balance.", "danger")
            return redirect("/")
        time = current_time()
        found = False
        rows = db.execute("SELECT symbol FROM portfolio WHERE user_id = ?", session["user_id"])
        for dict in rows:
            if symbol in dict.values():
                found = True
                break
        if found:
            db.execute("UPDATE portfolio SET shares=shares+? WHERE user_id=? AND symbol=?", shares, session["user_id"], symbol)
        else:
            db.execute("INSERT INTO portfolio (user_id, symbol, name, shares, price) VALUES(?, ?, ?, ?, ?)", session["user_id"], symbol, name, shares, price)
        db.execute("INSERT INTO history (user_id, symbol, name, shares, price, time) VALUES(?, ?, ?, ?, ?, ?)", session["user_id"], symbol, name, shares, price, time)
        db.execute("UPDATE users SET cash=cash-? WHERE id=?", (float(shares) * float(price)), session["user_id"])
        count2 = len(rows)
        count = db.execute("SELECT COUNT(*) FROM history WHERE user_id = ?", session["user_id"])
        count = count[0]['COUNT(*)']
        if count2 > 20:
            flash("Reached limit of 20 stokcs. Please sell current stocks to purchase more.", "danger")
            return redirect("/portfolio")
        if count > 10:
            db.execute("DELETE FROM history WHERE rowid = (SELECT rowid FROM history WHERE user_id = ? ORDER BY time ASC LIMIT 1)", session["user_id"])
        flash("Purchased.", "success")
        return redirect("/")


@app.route("/sell", methods=["POST"])
@login_required
def sell():
    symbol = request.form.get("symbol")
    name = request.form.get("name")
    shares = request.form.get("shares")
    stock_info = lookup(symbol, name)
    if stock_info == None:
        flash("Unable to sell.", "danger")
        return redirect("/")
    else:
        price = stock_info["price"]
        balance = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
        time = current_time()
        found = False
        rows = db.execute("SELECT shares FROM portfolio WHERE user_id = ? AND symbol = ?", session["user_id"], symbol)
        shares_owned = rows[0]["shares"]
        if int(shares) < shares_owned:
            db.execute("UPDATE portfolio SET shares=shares-? WHERE user_id=? AND symbol=?", shares, session["user_id"], symbol)
        else:
            db.execute("DELETE FROM portfolio WHERE user_id = ? AND symbol = ?", session["user_id"], symbol)
        db.execute("INSERT INTO history (user_id, symbol, name, shares, price, time) VALUES(?, ?, ?, ?, ?, ?)", session["user_id"], symbol, name, int(shares) * -1, price, time)
        db.execute("UPDATE users SET cash=cash+? WHERE id=?", (float(shares) * float(price)), session["user_id"])
        flash("Sold.", "success")
        return redirect("/")

@app.route("/balance", methods=["POST"])
@login_required
def balance():
    balance = request.form.get("balance")
    db.execute("UPDATE users SET cash=? WHERE id=?", balance, session["user_id"])
    flash("Changed Balance.", "success")
    return redirect("/")