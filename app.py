import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"  # replace with env var in production

with app.app_context():
    init_db()
    seed_db()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def resolve_date_range(range_value, start_arg, end_arg):
    """Returns (normalized_range_value, start_date, end_date) — the normalized
    range value is the single source of truth for which option is actually
    selected, so callers never need a second, separately maintained check."""
    today = date.today()

    if range_value == "this-month":
        return "this-month", today.replace(day=1).isoformat(), today.isoformat()

    if range_value == "last-month":
        first_of_this_month = today.replace(day=1)
        last_of_last_month = first_of_this_month - timedelta(days=1)
        return "last-month", last_of_last_month.replace(day=1).isoformat(), last_of_last_month.isoformat()

    if range_value == "last-30-days":
        return "last-30-days", (today - timedelta(days=29)).isoformat(), today.isoformat()

    if range_value == "custom":
        try:
            start = datetime.strptime(start_arg, "%Y-%m-%d").date()
            end = datetime.strptime(end_arg, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return "all", None, None
        if start > end:
            return "all", None, None
        return "custom", start.isoformat(), end.isoformat()

    return "all", None, None  # "all", missing, or unrecognized


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm  = request.form.get("confirm_password", "")

    if not name or not email or not password or not confirm:
        return render_template("register.html", error="All fields are required.")
    if password != confirm:
        return render_template("register.html", error="Passwords do not match.")

    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return render_template("register.html", error="An account with that email already exists.")
    finally:
        conn.close()

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="All fields are required.")

    conn = get_db()
    user = conn.execute(
        "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"]   = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
@login_required
def profile():
    user = get_user_by_id(session["user_id"])

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    range_arg = request.args.get("range", "all")
    start_arg = request.args.get("start")
    end_arg = request.args.get("end")

    range_value, start_date, end_date = resolve_date_range(range_arg, start_arg, end_arg)

    stats = get_summary_stats(session["user_id"], start_date, end_date)

    return render_template(
        "profile.html",
        user=user,
        total_spent=stats["total_spent"],
        transaction_count=stats["transaction_count"],
        top_category=stats["top_category"],
        recent_transactions=get_recent_transactions(session["user_id"], start_date=start_date, end_date=end_date),
        category_breakdown=get_category_breakdown(session["user_id"], start_date, end_date),
        selected_range=range_value,
        start_value=start_date if range_value == "custom" else "",
        end_value=end_date if range_value == "custom" else "",
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
