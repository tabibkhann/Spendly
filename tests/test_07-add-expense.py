"""
Tests for Spec 07 — Add Expense
(.claude/specs/07-add-expense.md)

Covers:
  - Auth guard: GET/POST /expenses/add redirect to /login when logged out,
    and an unauthenticated POST never writes to the DB
  - GET /expenses/add (logged in) renders a form with amount, category,
    date, and description fields, offering the full category list
  - POST with valid amount/category/date creates a row scoped to
    session["user_id"] and redirects (302) to /profile — never trusting
    a client-supplied user_id
  - The new expense is reflected in /profile's total spent, recent
    transactions, and category breakdown, and stays scoped to its owner
  - Validation errors (missing/zero/negative/non-numeric amount,
    missing/blank category, missing/invalid/malformed date) re-render the
    form with an `auth-error`-style message and insert no row, while
    preserving the user's other entered field values
  - `description` is optional; blank/missing description still saves
  - Edge cases: SQL-injection-style input, very long description, very
    small/large positive amounts are all handled safely
  - /profile exposes a visible link/button to /expenses/add
"""

import re

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


def _get_expenses_for_user(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, user_id, amount, category, date, description FROM expenses "
        "WHERE user_id = ? ORDER BY id",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _count_all_expenses():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) AS c FROM expenses").fetchone()["c"]
    conn.close()
    return count


def _extract_input_value(body, name):
    match = re.search(rf'<input[^>]*name=["\']{name}["\'][^>]*>', body, re.IGNORECASE)
    assert match, f'Could not find <input name="{name}"> in response body'
    tag = match.group(0)
    value_match = re.search(r'value=["\']([^"\']*)["\']', tag)
    return value_match.group(1) if value_match else ""


def _extract_select_block(body, name):
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


VALID_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def _valid_payload(**overrides):
    payload = {
        "amount": "42.50",
        "category": "Food",
        "date": "2026-05-15",
        "description": "Groceries",
    }
    payload.update(overrides)
    return payload


def _login_ada(client):
    register_and_login(client, "Ada Lovelace", "ada@spendly.com", "password123")
    return _get_user_id("ada@spendly.com")


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #

class TestAuthGuard:
    def test_get_add_expense_redirects_to_login_when_logged_out(self, client):
        response = client.get("/expenses/add")
        assert response.status_code == 302, "Logged-out GET must redirect"
        assert "/login" in response.headers["Location"], "Should redirect to /login"

    def test_post_add_expense_redirects_to_login_when_logged_out(self, client):
        response = client.post("/expenses/add", data=_valid_payload())
        assert response.status_code == 302, "Logged-out POST must redirect"
        assert "/login" in response.headers["Location"], "Should redirect to /login"

    def test_post_add_expense_while_logged_out_inserts_nothing(self, client):
        count_before = _count_all_expenses()
        client.post("/expenses/add", data=_valid_payload())
        count_after = _count_all_expenses()
        assert count_before == count_after, "Unauthenticated POST must not write to the DB"


# ------------------------------------------------------------------ #
# GET renders the form                                                #
# ------------------------------------------------------------------ #

class TestRenderForm:
    def test_get_add_expense_when_logged_in_returns_200_with_form_fields(self, client):
        _login_ada(client)

        response = client.get("/expenses/add")
        body = response.data.decode()

        assert response.status_code == 200, "Logged-in GET should render the form"
        assert 'name="amount"' in body, "Expected an amount field"
        assert 'name="category"' in body, "Expected a category field"
        assert 'name="date"' in body, "Expected a date field"
        assert 'name="description"' in body, "Expected a description field"

    def test_get_add_expense_lists_all_expected_categories(self, client):
        _login_ada(client)

        response = client.get("/expenses/add")
        select_block = _extract_select_block(response.data.decode(), "category")

        for category in VALID_CATEGORIES:
            assert f">{category}<" in select_block or f'value="{category}"' in select_block, (
                f"Expected category '{category}' to be offered as an option "
                "(matching seed_db()'s category list)"
            )


# ------------------------------------------------------------------ #
# Happy path — valid submission                                       #
# ------------------------------------------------------------------ #

class TestValidSubmission:
    def test_valid_submission_redirects_to_profile(self, client):
        _login_ada(client)

        response = client.post("/expenses/add", data=_valid_payload(), follow_redirects=False)

        assert response.status_code == 302, "Valid submission should redirect, not render directly"
        assert response.headers["Location"].endswith("/profile"), (
            "Successful submission should redirect to /profile"
        )

    def test_valid_submission_does_not_render_page_content_directly(self, client):
        """A 302 response body must not contain the submitted data — this
        guards against the form being re-rendered instead of redirecting,
        which would let a page refresh resubmit the form."""
        _login_ada(client)

        response = client.post("/expenses/add", data=_valid_payload(description="UniqueMarkerXYZ"))

        assert response.status_code == 302
        assert b"UniqueMarkerXYZ" not in response.data

    def test_valid_submission_inserts_row_scoped_to_current_user(self, client):
        user_id = _login_ada(client)

        client.post("/expenses/add", data=_valid_payload(
            amount="42.50", category="Food", date="2026-05-15", description="Groceries"
        ))

        rows = _get_expenses_for_user(user_id)
        assert len(rows) == 1, "Expected exactly one row to be inserted"
        row = rows[0]
        assert row["user_id"] == user_id, "Row must be attached to the logged-in user"
        assert row["amount"] == pytest.approx(42.50)
        assert row["category"] == "Food"
        assert row["date"] == "2026-05-15"
        assert row["description"] == "Groceries"

    def test_client_supplied_user_id_field_is_ignored(self, client):
        """New expenses must always be attached to session['user_id'] —
        never trust a client-supplied user id, even if one is smuggled
        into the POST body."""
        ada_id = _login_ada(client)
        client.get("/logout")

        register_and_login(client, "Grace Hopper", "grace@spendly.com", "password123")
        grace_id = _get_user_id("grace@spendly.com")

        client.post("/expenses/add", data=_valid_payload(user_id=str(ada_id)))

        assert _get_expenses_for_user(grace_id) != [], "Expense should attach to the logged-in user"
        assert len(_get_expenses_for_user(grace_id)) == 1
        assert _get_expenses_for_user(ada_id) == [], "Spoofed user_id in the POST body must be ignored"

    def test_new_expense_reflected_in_profile_total_and_recent_transactions(self, client):
        _login_ada(client)

        client.post("/expenses/add", data=_valid_payload(
            amount="42.50", category="Food", date="2026-05-15", description="UniqueGroceriesDesc"
        ))

        response = client.get("/profile")
        body = response.data.decode()

        assert response.status_code == 200
        assert "₹42.50" in body, "Total spent should reflect the new expense"
        assert "UniqueGroceriesDesc" in body, "Recent transactions should list the new expense"
        assert "Food" in body

    def test_new_expense_reflected_in_category_breakdown(self, client):
        _login_ada(client)

        client.post("/expenses/add", data=_valid_payload(
            amount="100.00", category="Entertainment", date="2026-05-15", description="Movie night"
        ))

        body = client.get("/profile").data.decode()
        assert "Entertainment" in body, "Category breakdown should include the new category"
        assert "₹100.00" in body

    def test_new_expense_not_visible_to_a_different_user(self, client):
        _login_ada(client)
        client.post("/expenses/add", data=_valid_payload(
            amount="42.50", category="Food", date="2026-05-15", description="OnlyAdaShouldSeeThis"
        ))
        client.get("/logout")

        register_and_login(client, "Grace Hopper", "grace@spendly.com", "password123")
        body = client.get("/profile").data.decode()

        assert "OnlyAdaShouldSeeThis" not in body, "Expenses must not leak across users"
        assert "₹0.00" in body


# ------------------------------------------------------------------ #
# Amount validation                                                   #
# ------------------------------------------------------------------ #

class TestAmountValidation:
    @pytest.mark.parametrize(
        "bad_amount",
        ["", "0", "0.00", "-5", "-0.01", "abc", "12abc"],
        ids=[
            "blank",
            "zero",
            "zero-decimal",
            "negative",
            "negative-decimal",
            "non-numeric",
            "trailing-letters",
        ],
    )
    def test_invalid_amount_rerenders_form_with_error_and_no_insert(self, client, bad_amount):
        user_id = _login_ada(client)

        response = client.post("/expenses/add", data=_valid_payload(amount=bad_amount))
        body = response.data.decode()

        assert response.status_code == 200, "Invalid amount should re-render the form, not redirect"
        assert "auth-error" in body, "Expected an auth-error-style validation message"
        assert _get_expenses_for_user(user_id) == [], "No row should be inserted for invalid amount"

    def test_missing_amount_field_rerenders_form_with_error_and_no_insert(self, client):
        user_id = _login_ada(client)
        payload = _valid_payload()
        del payload["amount"]

        response = client.post("/expenses/add", data=payload)

        assert response.status_code == 200
        assert _get_expenses_for_user(user_id) == []

    def test_nan_amount_is_rejected_as_not_a_positive_number(self, client):
        """'NaN' is not a valid positive monetary amount even though
        Python's float() will parse the literal string."""
        user_id = _login_ada(client)

        response = client.post("/expenses/add", data=_valid_payload(amount="NaN"))

        assert response.status_code == 200, "NaN must not be accepted as a valid amount"
        assert _get_expenses_for_user(user_id) == [], "NaN must not be inserted as an expense amount"

    def test_very_small_positive_amount_is_accepted(self, client):
        user_id = _login_ada(client)

        response = client.post("/expenses/add", data=_valid_payload(amount="0.01"))

        assert response.status_code == 302
        rows = _get_expenses_for_user(user_id)
        assert rows[0]["amount"] == pytest.approx(0.01)

    def test_large_amount_is_accepted(self, client):
        user_id = _login_ada(client)

        response = client.post("/expenses/add", data=_valid_payload(amount="999999.99"))

        assert response.status_code == 302
        rows = _get_expenses_for_user(user_id)
        assert rows[0]["amount"] == pytest.approx(999999.99)


# ------------------------------------------------------------------ #
# Category validation                                                 #
# ------------------------------------------------------------------ #

class TestCategoryValidation:
    def test_blank_category_rerenders_form_with_error_and_no_insert(self, client):
        user_id = _login_ada(client)

        response = client.post("/expenses/add", data=_valid_payload(category=""))
        body = response.data.decode()

        assert response.status_code == 200
        assert "auth-error" in body
        assert _get_expenses_for_user(user_id) == []

    def test_missing_category_field_rerenders_form_with_error_and_no_insert(self, client):
        user_id = _login_ada(client)
        payload = _valid_payload()
        del payload["category"]

        response = client.post("/expenses/add", data=payload)

        assert response.status_code == 200
        assert _get_expenses_for_user(user_id) == []


# ------------------------------------------------------------------ #
# Date validation                                                     #
# ------------------------------------------------------------------ #

class TestDateValidation:
    @pytest.mark.parametrize(
        "bad_date",
        ["", "not-a-date", "2026/05/15", "05-15-2026", "2026-13-40", "2026-02-30", "15-05-2026"],
        ids=[
            "blank",
            "garbage",
            "slash-format",
            "us-format",
            "invalid-month",
            "invalid-day-feb30",
            "day-month-year",
        ],
    )
    def test_invalid_date_rerenders_form_with_error_and_no_insert(self, client, bad_date):
        user_id = _login_ada(client)

        response = client.post("/expenses/add", data=_valid_payload(date=bad_date))
        body = response.data.decode()

        assert response.status_code == 200, "Invalid date should re-render the form, not redirect"
        assert "auth-error" in body
        assert _get_expenses_for_user(user_id) == [], "No row should be inserted for invalid date"

    def test_missing_date_field_rerenders_form_with_error_and_no_insert(self, client):
        user_id = _login_ada(client)
        payload = _valid_payload()
        del payload["date"]

        response = client.post("/expenses/add", data=payload)

        assert response.status_code == 200
        assert _get_expenses_for_user(user_id) == []


# ------------------------------------------------------------------ #
# Form value preservation on validation error                         #
# ------------------------------------------------------------------ #

class TestFormValuePreservationOnError:
    def test_invalid_amount_preserves_other_entered_values(self, client):
        _login_ada(client)

        response = client.post("/expenses/add", data=_valid_payload(
            amount="-5", category="Bills", date="2026-06-01", description="Keep me"
        ))
        body = response.data.decode()

        assert _extract_input_value(body, "date") == "2026-06-01"
        assert _extract_input_value(body, "description") == "Keep me"
        select_block = _extract_select_block(body, "category")
        assert _selected_option_value(select_block) == "Bills"

    def test_invalid_date_preserves_other_entered_values(self, client):
        _login_ada(client)

        response = client.post("/expenses/add", data=_valid_payload(
            amount="77.25", category="Health", date="not-a-date", description="Keep me too"
        ))
        body = response.data.decode()

        assert _extract_input_value(body, "amount") == "77.25"
        assert _extract_input_value(body, "description") == "Keep me too"
        select_block = _extract_select_block(body, "category")
        assert _selected_option_value(select_block) == "Health"


# ------------------------------------------------------------------ #
# description is optional                                             #
# ------------------------------------------------------------------ #

class TestDescriptionOptional:
    def test_blank_description_is_allowed_and_expense_saves(self, client):
        user_id = _login_ada(client)

        response = client.post("/expenses/add", data=_valid_payload(description=""))

        assert response.status_code == 302, "Blank description must not block submission"
        rows = _get_expenses_for_user(user_id)
        assert len(rows) == 1
        assert rows[0]["description"] in ("", None)

    def test_missing_description_field_is_allowed_and_expense_saves(self, client):
        user_id = _login_ada(client)
        payload = _valid_payload()
        del payload["description"]

        response = client.post("/expenses/add", data=payload)

        assert response.status_code == 302, "Missing description must not block submission"
        assert len(_get_expenses_for_user(user_id)) == 1


# ------------------------------------------------------------------ #
# Edge cases / DB safety                                              #
# ------------------------------------------------------------------ #

class TestEdgeCasesAndSafety:
    def test_description_with_sql_injection_attempt_is_stored_literally(self, client):
        user_id = _login_ada(client)
        malicious = "'; DROP TABLE expenses; --"

        response = client.post("/expenses/add", data=_valid_payload(description=malicious))

        assert response.status_code == 302, "A crafted description must not break the insert"
        rows = _get_expenses_for_user(user_id)
        assert len(rows) == 1
        assert rows[0]["description"] == malicious, "Input should be stored literally, not executed"

        conn = get_db()
        count = conn.execute("SELECT COUNT(*) AS c FROM expenses").fetchone()["c"]
        conn.close()
        assert count >= 1, "The expenses table must still exist after a SQL-injection attempt"

    def test_very_long_description_is_accepted(self, client):
        user_id = _login_ada(client)
        long_description = "x" * 5000

        response = client.post("/expenses/add", data=_valid_payload(description=long_description))

        assert response.status_code == 302
        rows = _get_expenses_for_user(user_id)
        assert rows[0]["description"] == long_description


# ------------------------------------------------------------------ #
# Entry point from /profile                                           #
# ------------------------------------------------------------------ #

class TestEntryPointFromProfile:
    def test_profile_page_links_to_add_expense_form(self, client):
        _login_ada(client)

        body = client.get("/profile").data.decode()

        assert "/expenses/add" in body, "Profile page should link to the add-expense form"
