from datetime import datetime

import pytest

from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)
from conftest import register_and_login


# ------------------------------------------------------------------ #
# Unit tests                                                          #
# ------------------------------------------------------------------ #

def test_get_user_by_id_valid(seeded_db):
    user = get_user_by_id(seeded_db["seed_user_id"])
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert user["member_since"] == datetime.now().strftime("%B %Y")


def test_get_user_by_id_missing(seeded_db):
    assert get_user_by_id(seeded_db["seed_user_id"] + 9999) is None


def test_get_summary_stats_with_expenses(seeded_db):
    stats = get_summary_stats(seeded_db["seed_user_id"])
    assert stats["total_spent"] == pytest.approx(330.64)
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(seeded_db):
    stats = get_summary_stats(seeded_db["empty_user_id"])
    assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}


def test_get_recent_transactions_with_expenses(seeded_db):
    transactions = get_recent_transactions(seeded_db["seed_user_id"])
    assert len(transactions) == 8
    dates = [tx["date"] for tx in transactions]
    assert dates == sorted(dates, reverse=True)
    for tx in transactions:
        assert set(tx.keys()) == {"date", "description", "category", "amount"}


def test_get_recent_transactions_no_expenses(seeded_db):
    assert get_recent_transactions(seeded_db["empty_user_id"]) == []


def test_get_category_breakdown_with_expenses(seeded_db):
    breakdown = get_category_breakdown(seeded_db["seed_user_id"])
    assert len(breakdown) == 7
    amounts = [cat["amount"] for cat in breakdown]
    assert amounts == sorted(amounts, reverse=True)
    pcts = [cat["pct"] for cat in breakdown]
    assert all(isinstance(pct, int) for pct in pcts)
    assert sum(pcts) == 100


def test_get_category_breakdown_no_expenses(seeded_db):
    assert get_category_breakdown(seeded_db["empty_user_id"]) == []


# ------------------------------------------------------------------ #
# Route tests                                                         #
# ------------------------------------------------------------------ #

def test_profile_redirects_when_unauthenticated(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated_seed_user(client):
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    response = client.get("/profile")
    body = response.data.decode()

    assert response.status_code == 200
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹330.64" in body
    assert "Bills" in body
    for category in ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]:
        assert category in body

    assert body.find("2026-08-24") < body.find("2026-08-01")


def test_profile_new_user_no_expenses(client):
    register_and_login(client, "New Person", "newperson@spendly.com", "password123")
    response = client.get("/profile")
    body = response.data.decode()

    assert response.status_code == 200
    assert "₹0.00" in body
    assert "No expenses yet." in body
