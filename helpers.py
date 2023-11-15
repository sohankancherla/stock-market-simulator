import csv
import datetime
import pytz
import requests
import subprocess
import urllib
import uuid

from config import API_KEY
from flask import redirect, render_template, session
from functools import wraps

# Replace API_KEY with your own API key
api_key=API_KEY

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol, name):
    """Look up quote for symbol."""

    # Prepare API request
    symbol = symbol

    # Finnhub API
    url = (f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}")

    # Query API
    try:
        response = requests.get(url)
        response = requests.get(url)
        data = response.json()
        price = data["c"]
        change = data["d"]
        if change != None and price != None:
            return {
                "name": name,
                "price": price,
                "change": change,
                "symbol": symbol
            }
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


def usd(value):
    """Format value as USD."""
    if value >= 0:
        return f"${value:,.2f}"
    else:
        return f"-${abs(value):,.2f}"
