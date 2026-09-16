from datetime import datetime

from database.db import get_db


def _date_filter_clause(start_date, end_date):
    if start_date and end_date:
        return " AND date BETWEEN ? AND ?", [start_date, end_date]
    return "", []


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return None

    member_since = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "member_since": member_since,
    }


def get_summary_stats(user_id, start_date=None, end_date=None):
    conn = get_db()
    clause, extra = _date_filter_clause(start_date, end_date)
    totals = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total_spent, COUNT(*) AS transaction_count "
        "FROM expenses WHERE user_id = ?" + clause,
        [user_id] + extra,
    ).fetchone()

    if totals["transaction_count"] == 0:
        conn.close()
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    top = conn.execute(
        "SELECT category FROM expenses WHERE user_id = ?" + clause + " "
        "GROUP BY category ORDER BY SUM(amount) DESC, category ASC LIMIT 1",
        [user_id] + extra,
    ).fetchone()
    conn.close()

    return {
        "total_spent": totals["total_spent"],
        "transaction_count": totals["transaction_count"],
        "top_category": top["category"],
    }


def get_recent_transactions(user_id, limit=10, *, start_date=None, end_date=None):
    conn = get_db()
    clause, extra = _date_filter_clause(start_date, end_date)
    rows = conn.execute(
        "SELECT date, description, category, amount FROM expenses "
        "WHERE user_id = ?" + clause + " ORDER BY date DESC, id DESC LIMIT ?",
        [user_id] + extra + [limit],
    ).fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_category_breakdown(user_id, start_date=None, end_date=None):
    conn = get_db()
    clause, extra = _date_filter_clause(start_date, end_date)
    rows = conn.execute(
        "SELECT category, SUM(amount) AS total FROM expenses "
        "WHERE user_id = ?" + clause + " GROUP BY category ORDER BY total DESC, category ASC",
        [user_id] + extra,
    ).fetchall()
    conn.close()

    if not rows:
        return []

    grand_total = sum(row["total"] for row in rows)
    breakdown = [{"name": row["category"], "amount": row["total"]} for row in rows]

    rounded_pcts = [round(item["amount"] / grand_total * 100) for item in breakdown]
    remainder = 100 - sum(rounded_pcts)
    rounded_pcts[0] += remainder

    for item, pct in zip(breakdown, rounded_pcts):
        item["pct"] = pct

    return breakdown
