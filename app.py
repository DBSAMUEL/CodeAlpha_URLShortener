"""CodeAlpha Backend Internship - Task 1: Simple URL Shortener (Flask + SQLite)."""
import os
import re
import secrets
import sqlite3
import string
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Flask, abort, g, jsonify, redirect, render_template, request

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "urls.db"))
ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
MAX_URL_LENGTH = 2048

app = Flask(__name__)


# ---------- Database ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT NOT NULL UNIQUE,
                original_url TEXT NOT NULL,
                clicks INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_original ON urls(original_url)")


# ---------- Helpers ----------
def is_valid_url(url: str) -> bool:
    if not url or len(url) > MAX_URL_LENGTH:
        return False
    parsed = urlparse(url)
    try:
        parsed.port  # raises ValueError on a bad port
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.hostname)


def normalize(url: str) -> str:
    url = url.strip()
    # Leave scheme-like input (javascript:, mailto:, ...) untouched so validation rejects it.
    if "://" not in url and not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:(?!\d)", url):
        url = "https://" + url
    return url


def generate_code(db) -> str:
    """Generate a random unique short code, retrying on collision."""
    length = CODE_LENGTH
    while True:
        for _ in range(5):
            code = "".join(secrets.choice(ALPHABET) for _ in range(length))
            if not db.execute("SELECT 1 FROM urls WHERE short_code = ?", (code,)).fetchone():
                return code
        length += 1  # space getting crowded: use longer codes


# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/shorten", methods=["POST"])
def shorten():
    data = request.get_json(silent=True) or request.form
    long_url = normalize(data.get("url", ""))
    if not is_valid_url(long_url):
        return jsonify(error="Please provide a valid http(s) URL."), 400

    db = get_db()
    existing = db.execute(
        "SELECT short_code FROM urls WHERE original_url = ?", (long_url,)
    ).fetchone()
    if existing:
        code, status = existing["short_code"], 200
    else:
        code = generate_code(db)
        db.execute(
            "INSERT INTO urls (short_code, original_url, created_at) VALUES (?, ?, ?)",
            (code, long_url, datetime.now(timezone.utc).isoformat()),
        )
        db.commit()
        status = 201

    return jsonify(
        short_code=code,
        short_url=request.host_url + code,
        original_url=long_url,
    ), status


@app.route("/api/stats/<code>")
def stats(code):
    row = get_db().execute("SELECT * FROM urls WHERE short_code = ?", (code,)).fetchone()
    if not row:
        return jsonify(error="Short code not found."), 404
    return jsonify(
        short_code=row["short_code"],
        original_url=row["original_url"],
        clicks=row["clicks"],
        created_at=row["created_at"],
    )


@app.route("/<code>")
def follow(code):
    db = get_db()
    row = db.execute("SELECT original_url FROM urls WHERE short_code = ?", (code,)).fetchone()
    if not row:
        abort(404)
    db.execute("UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?", (code,))
    db.commit()
    return redirect(row["original_url"], code=302)


@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/"):
        return jsonify(error="Not found."), 404
    return render_template("index.html", error="That short link doesn't exist."), 404


init_db()

if __name__ == "__main__":
    app.run(debug=True)
