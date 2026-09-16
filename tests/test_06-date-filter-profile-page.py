"""
Tests for Spec 06 — Date Filter For Profile Page
(.claude/specs/06-date-filter-profile-page.md)

Covers:
  - GET /profile?range=... query params (all, this-month, last-month,
    last-30-days, custom)
  - Auth guard on the (already protected) /profile route with filter params
  - Fallback to range=all for invalid/malformed custom ranges (no 500s)
  - DB-driven stats (total spent, transaction count, category breakdown,
    recent transactions) reflecting the selected date range
  - Filter form re-rendering the active range/dates after reload
  - profile.css using CSS variables instead of hardcoded hex colours

These tests never assume future/forward-dated expenses; all "in range" /
"out of range" fixture data is anchored relative to `date.today()` (for the
calendar-relative ranges) or to fixed historical dates (for the custom
range), so the suite is correct no matter what day it actually runs on.
"""

import os
import re
from datetime import date, timedelta

import pytest

from database.db import get_db
from conftest import register_and_login


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _get_user_id(email):
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    assert row is not None, f"Expected a user with email {email} to exist"
    return row["id"]


def _insert_expense(user_id, amount, category, expense_date, description):
    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, expense_date, description),
    )
    conn.commit()
    conn.close()


def _get_query(client, params):
    """GET /profile with only the provided (non-None) query params."""
    clean_params = {k: v for k, v in params.items() if v is not None}
    return client.get("/profile", query_string=clean_params)


def _extract_select_block(body, name="range"):
    match = re.search(
        rf'<select[^>]*name=["\']?{name}["\']?[^>]*>.*?</select>',
        body,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, f'Could not find <select name="{name}"> in response body'
    return match.group(0)


def _selected_option_value(select_block):
    match = re.search(
        r'<option[^>]*value=["\']([^"\']+)["\'][^>]*selected', select_block, re.IGNORECASE
    )
    if match:
        return match.group(1)
    match = re.search(
        r'<option[^>]*selected[^>]*value=["\']([^"\']+)["\']', select_block, re.IGNORECASE
    )
    if match:
        return match.group(1)
    return None


def _extract_input_value(body, name):
    match = re.search(rf'<input[^>]*name=["\']{name}["\'][^>]*>', body, re.IGNORECASE)
    assert match, f'Could not find <input name="{name}"> in response body'
    tag = match.group(0)
    value_match = re.search(r'value=["\']([^"\']*)["\']', tag)
    return value_match.group(1) if value_match else ""


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def range_client(client):
    """A logged-in client for a brand-new user with no seeded expenses,
    so date-range assertions aren't polluted by the Aug-2026 demo data."""
    register_and_login(client, "Range Tester", "rangetester@spendly.com", "password123")
    user_id = _get_user_id("rangetester@spendly.com")
    return client, user_id


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "params",
    [
        {},
        {"range": "this-month"},
        {"range": "last-month"},
        {"range": "last-30-days"},
        {"range": "custom", "start": "2026-08-01", "end": "2026-08-15"},
        {"range": "bogus"},
    ],
)
def test_profile_with_filter_params_redirects_when_unauthenticated(client, params):
    response = _get_query(client, params)
    assert response.status_code == 302, "Unauthenticated request should redirect"
    assert "/login" in response.headers["Location"], "Should redirect to login"


# ------------------------------------------------------------------ #
# Default / all-time behaviour                                        #
# ------------------------------------------------------------------ #

def test_profile_no_query_params_behaves_as_all_time(client):
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    response = client.get("/profile")
    body = response.data.decode()

    assert response.status_code == 200
    assert "₹330.64" in body
    assert "Bills" in body


def test_profile_range_all_matches_default_no_params(client):
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    default_body = client.get("/profile").data.decode()
    explicit_all_body = client.get("/profile", query_string={"range": "all"}).data.decode()

    assert "₹330.64" in default_body
    assert "₹330.64" in explicit_all_body
    assert default_body.count("₹330.64") == explicit_all_body.count("₹330.64")


def test_profile_range_all_select_is_selected_by_default(client):
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    body = client.get("/profile").data.decode()
    select_block = _extract_select_block(body)
    assert _selected_option_value(select_block) == "all", (
        "With no query params, the 'All time' option should be selected"
    )


# ------------------------------------------------------------------ #
# this-month                                                          #
# ------------------------------------------------------------------ #

def test_this_month_shows_only_current_month_expenses(range_client):
    client, user_id = range_client
    today = date.today()
    first_of_this_month = today.replace(day=1)
    out_of_month_date = (first_of_this_month - timedelta(days=1)).isoformat()

    _insert_expense(user_id, 100.00, "Food", today.isoformat(), "InCurrentMonthExpense")
    _insert_expense(user_id, 50.00, "Transport", out_of_month_date, "PreviousMonthExpense")

    response = _get_query(client, {"range": "this-month"})
    body = response.data.decode()

    assert response.status_code == 200
    assert "₹100.00" in body
    assert "InCurrentMonthExpense" in body
    assert "PreviousMonthExpense" not in body
    assert "Transport" not in body


def test_this_month_no_matching_expenses_shows_empty_state(range_client):
    client, user_id = range_client
    today = date.today()
    first_of_this_month = today.replace(day=1)
    out_of_month_date = (first_of_this_month - timedelta(days=1)).isoformat()

    _insert_expense(user_id, 50.00, "Transport", out_of_month_date, "PreviousMonthExpense")

    response = _get_query(client, {"range": "this-month"})
    body = response.data.decode()

    assert response.status_code == 200
    assert "₹0.00" in body
    assert "No expenses yet." in body
    assert "PreviousMonthExpense" not in body


# ------------------------------------------------------------------ #
# last-month                                                          #
# ------------------------------------------------------------------ #

def test_last_month_shows_only_previous_calendar_month_expenses(range_client):
    client, user_id = range_client
    today = date.today()
    first_of_this_month = today.replace(day=1)
    last_of_last_month = first_of_this_month - timedelta(days=1)
    first_of_last_month = last_of_last_month.replace(day=1)
    mid_last_month = (first_of_last_month + timedelta(days=10)).isoformat()
    two_months_ago = (first_of_last_month - timedelta(days=1)).isoformat()

    _insert_expense(user_id, 75.00, "Bills", mid_last_month, "LastMonthExpense")
    _insert_expense(user_id, 20.00, "Food", today.isoformat(), "ThisMonthExpense")
    _insert_expense(user_id, 15.00, "Shopping", two_months_ago, "TwoMonthsAgoExpense")

    response = _get_query(client, {"range": "last-month"})
    body = response.data.decode()

    assert response.status_code == 200
    assert "₹75.00" in body
    assert "LastMonthExpense" in body
    assert "ThisMonthExpense" not in body
    assert "TwoMonthsAgoExpense" not in body


# ------------------------------------------------------------------ #
# last-30-days                                                        #
# ------------------------------------------------------------------ #

def test_last_30_days_includes_recent_excludes_older(range_client):
    client, user_id = range_client
    today = date.today()
    recent_date = (today - timedelta(days=10)).isoformat()
    old_date = (today - timedelta(days=45)).isoformat()

    _insert_expense(user_id, 40.00, "Food", recent_date, "RecentWithinRangeExpense")
    _insert_expense(user_id, 60.00, "Health", old_date, "TooOldExpense")

    response = _get_query(client, {"range": "last-30-days"})
    body = response.data.decode()

    assert response.status_code == 200
    assert "₹40.00" in body
    assert "RecentWithinRangeExpense" in body
    assert "TooOldExpense" not in body
    assert "Health" not in body


# ------------------------------------------------------------------ #
# custom range                                                        #
# ------------------------------------------------------------------ #

def test_custom_range_is_inclusive_of_both_boundaries(range_client):
    client, user_id = range_client

    _insert_expense(user_id, 10.00, "Food", "2021-05-10", "StartBoundaryExpense")
    _insert_expense(user_id, 20.00, "Bills", "2021-05-15", "MiddleExpense")
    _insert_expense(user_id, 30.00, "Health", "2021-05-20", "EndBoundaryExpense")
    _insert_expense(user_id, 5.00, "Shopping", "2021-05-09", "JustBeforeExpense")
    _insert_expense(user_id, 7.00, "Other", "2021-05-21", "JustAfterExpense")

    response = _get_query(
        client, {"range": "custom", "start": "2021-05-10", "end": "2021-05-20"}
    )
    body = response.data.decode()

    assert response.status_code == 200
    assert "₹60.00" in body, "Total should be 10 + 20 + 30 = 60.00 for the in-range expenses"
    assert "StartBoundaryExpense" in body
    assert "MiddleExpense" in body
    assert "EndBoundaryExpense" in body
    assert "JustBeforeExpense" not in body
    assert "JustAfterExpense" not in body


def test_custom_range_form_reflects_selected_dates(range_client):
    client, _ = range_client

    response = _get_query(
        client, {"range": "custom", "start": "2026-08-01", "end": "2026-08-15"}
    )
    body = response.data.decode()

    select_block = _extract_select_block(body)
    assert _selected_option_value(select_block) == "custom"
    assert _extract_input_value(body, "start") == "2026-08-01"
    assert _extract_input_value(body, "end") == "2026-08-15"


def test_non_custom_range_leaves_date_inputs_empty(range_client):
    client, _ = range_client

    response = _get_query(client, {"range": "this-month"})
    body = response.data.decode()

    assert _extract_input_value(body, "start") == ""
    assert _extract_input_value(body, "end") == ""


# ------------------------------------------------------------------ #
# Invalid / malformed params fall back to range=all, never a 500      #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "start,end",
    [
        (None, None),
        ("2026-08-10", None),
        (None, "2026-08-10"),
        ("2026-08-20", "2026-08-01"),
        ("not-a-date", "2026-08-10"),
        ("2026-08-01", "not-a-date"),
        ("2026-13-40", "2026-08-10"),
        ("", ""),
        ("2026-08-01' OR '1'='1", "2026-08-10"),
        ("a" * 500, "2026-08-10"),
    ],
    ids=[
        "both-missing",
        "end-missing",
        "start-missing",
        "start-after-end",
        "unparseable-start",
        "unparseable-end",
        "invalid-calendar-date",
        "both-empty",
        "sql-injection-attempt",
        "very-long-start",
    ],
)
def test_invalid_custom_range_falls_back_to_all_without_error(range_client, start, end):
    client, user_id = range_client
    _insert_expense(user_id, 42.00, "Food", "2026-08-05", "SomeExpense")

    response = _get_query(client, {"range": "custom", "start": start, "end": end})

    assert response.status_code == 200, "Invalid custom range must not error out"
    body = response.data.decode()
    select_block = _extract_select_block(body)
    assert _selected_option_value(select_block) == "all", (
        "Invalid custom range should silently fall back to 'all'"
    )
    # Falls back to all-time totals rather than an empty/error state.
    assert "₹42.00" in body


def test_unrecognized_range_value_falls_back_to_all(range_client):
    client, user_id = range_client
    _insert_expense(user_id, 42.00, "Food", "2026-08-05", "SomeExpense")

    response = _get_query(client, {"range": "not-a-real-range"})

    assert response.status_code == 200
    body = response.data.decode()
    select_block = _extract_select_block(body)
    assert _selected_option_value(select_block) == "all"
    assert "₹42.00" in body


# ------------------------------------------------------------------ #
# Consistency across stats / recent transactions / category breakdown #
# ------------------------------------------------------------------ #

def test_category_breakdown_reflects_selected_range(range_client):
    client, user_id = range_client
    today = date.today()
    first_of_this_month = today.replace(day=1)
    out_of_month_date = (first_of_this_month - timedelta(days=1)).isoformat()

    _insert_expense(user_id, 30.00, "Food", today.isoformat(), "InRangeFoodExpense")
    _insert_expense(user_id, 99.00, "Bills", out_of_month_date, "OutOfRangeBillsExpense")

    response = _get_query(client, {"range": "this-month"})
    body = response.data.decode()

    assert "Food" in body
    assert "Bills" not in body


def test_reloading_same_filtered_url_is_idempotent(range_client):
    client, user_id = range_client
    _insert_expense(user_id, 12.34, "Food", "2021-05-15", "StableExpense")

    params = {"range": "custom", "start": "2021-05-01", "end": "2021-05-31"}
    first_body = _get_query(client, params).data.decode()
    second_body = _get_query(client, params).data.decode()

    assert first_body == second_body, "Reloading the same filtered URL should be idempotent"
    assert "₹12.34" in first_body


def test_profile_read_only_filters_do_not_mutate_expenses_table(range_client):
    client, user_id = range_client
    _insert_expense(user_id, 12.34, "Food", "2021-05-15", "StableExpense")

    conn = get_db()
    count_before = conn.execute(
        "SELECT COUNT(*) AS c FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()["c"]
    conn.close()

    for params in (
        {"range": "this-month"},
        {"range": "last-month"},
        {"range": "last-30-days"},
        {"range": "custom", "start": "2021-05-01", "end": "2021-05-31"},
        {"range": "custom", "start": "bad", "end": "data"},
    ):
        _get_query(client, params)

    conn = get_db()
    count_after = conn.execute(
        "SELECT COUNT(*) AS c FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()["c"]
    conn.close()

    assert count_before == count_after == 1, "GET /profile filters must never write to the DB"


# ------------------------------------------------------------------ #
# CSS: only CSS variables, no hardcoded hex colours                   #
# ------------------------------------------------------------------ #

def test_profile_css_has_no_hardcoded_hex_colors():
    css_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "static",
        "css",
        "profile.css",
    )
    assert os.path.exists(css_path), "static/css/profile.css should exist"

    with open(css_path, "r", encoding="utf-8") as f:
        content = f.read()

    hex_color_pattern = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    matches = hex_color_pattern.findall(content)
    assert not matches, f"profile.css should use CSS variables, not hardcoded hex colours: {matches}"
