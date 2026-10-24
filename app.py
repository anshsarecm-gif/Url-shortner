import os
import secrets
import sqlite3
import string
from urllib.parse import urlparse

from flask import Flask, g, jsonify, redirect, render_template, request

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6

app = Flask(__name__)
app.config["DATABASE"] = os.environ.get("DATABASE", "urls.db")


# ---------- Database ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(app.config["DATABASE"]) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                clicks INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


# ---------- Helpers ----------
def is_valid_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def generate_code(db):
    for _ in range(10):
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        if db.execute("SELECT 1 FROM urls WHERE code = ?", (code,)).fetchone() is None:
            return code
    raise RuntimeError("Could not generate a unique code")


# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/shorten", methods=["POST"])
def shorten():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not is_valid_url(url):
        return jsonify(error="Please provide a valid http(s) URL."), 400

    db = get_db()
    code = generate_code(db)
    db.execute("INSERT INTO urls (code, original_url) VALUES (?, ?)", (code, url))
    db.commit()

    return jsonify(code=code, short_url=request.host_url + code, original_url=url), 201


@app.route("/api/stats/<code>")
def stats(code):
    row = get_db().execute("SELECT * FROM urls WHERE code = ?", (code,)).fetchone()
    if row is None:
        return jsonify(error="Not found"), 404
    return jsonify(
        code=row["code"],
        original_url=row["original_url"],
        clicks=row["clicks"],
        created_at=row["created_at"],
    )


@app.route("/<code>")
def follow(code):
    db = get_db()
    row = db.execute("SELECT original_url FROM urls WHERE code = ?", (code,)).fetchone()
    if row is None:
        return jsonify(error="Short link not found"), 404
    db.execute("UPDATE urls SET clicks = clicks + 1 WHERE code = ?", (code,))
    db.commit()
    return redirect(row["original_url"], code=302)


init_db()

if __name__ == "__main__":
    app.run(debug=True)
