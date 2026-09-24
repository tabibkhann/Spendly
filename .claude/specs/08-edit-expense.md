# Spec: Edit Expense

## Overview
This feature implements the "Edit Expense" flow, replacing the
`/expenses/<id>/edit` placeholder in `app.py`. It lets a logged-in
user update an existing expense they own (amount, category, date,
description) via a pre-filled form, so corrections don't require
deleting and re-adding a transaction. This is the second of the
three CRUD steps (add/edit/delete); delete remains a placeholder,
untouched by this step.

## Depends on
- Step 1 — `database/db.py` (schema: `expenses` table)
- Step 3 — Login/logout (session-based auth)
- Step 5 — Profile backend route (`get_user_by_id`, stats/query helpers)
- Step 7 — Add Expense (`insert_expense`, `EXPENSE_CATEGORIES`,
  validation pattern, `add_expense.html` markup to mirror)

## Routes
- `GET /expenses/<int:id>/edit` — render the edit form pre-filled
  with the expense's current values — logged-in only, owner only
- `POST /expenses/<int:id>/edit` — validate and update the expense,
  then redirect to `/profile` — logged-in only, owner only

If `id` does not exist, or exists but belongs to a different user,
redirect to `/profile` (do not leak whether the id exists for another
user — treat "not found" and "not yours" identically).

## Database changes
No schema changes. The existing `expenses` table
(`database/db.py`) already has all required columns. `id` must be
selected by `get_recent_transactions` (currently it is not) so
`profile.html` can link each row to its edit page.

## Templates
- **Create:** `templates/edit_expense.html` — same field set and
  markup pattern as `templates/add_expense.html` (`auth-section` /
  `form-group` / `form-input` / `btn-submit` / `auth-error`), but
  the form posts to `url_for('edit_expense', id=expense.id)` and
  every field is pre-filled with the expense's current values on
  first load.
- **Modify:** `templates/profile.html` — add an "Edit" link on each
  row in the recent-transactions list, pointing to
  `url_for('edit_expense', id=tx.id)`.

## Files to change
- `app.py` — replace the `edit_expense` placeholder route with
  `GET`/`POST` handling, `@login_required`, ownership check, form
  validation (reuse the same rules as `add_expense`), and update
  logic via a new `database/queries.py` helper.
- `database/queries.py` — add `get_expense_by_id(expense_id,
  user_id)` and `update_expense(expense_id, user_id, amount,
  category, date, description)`, both scoped by `user_id` in the
  `WHERE` clause (never trust the id alone). Add `id` to the
  `SELECT` in `get_recent_transactions`.
- `templates/profile.html` — add the per-row edit link.

## Files to create
- `templates/edit_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (n/a to this feature, but no new
  auth code should deviate from this)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate on the server exactly as in Step 7: `amount` must be a
  positive number, `category` must be from `EXPENSE_CATEGORIES`,
  `date` must be a valid `YYYY-MM-DD` date, `description` is
  optional. Re-render the form with an error message on invalid
  input — do not lose the user's other entered values.
- Every DB lookup and update for a specific expense must filter by
  both `id` AND `session["user_id"]` — a user must never be able to
  view or modify another user's expense by guessing or editing the
  URL's id (IDOR protection). If the row isn't found for that user,
  redirect to `/profile` rather than erroring.
- On success, redirect (`302`) to `/profile`, not render directly,
  so a page refresh doesn't resubmit the form.

## Definition of done
- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to
      `/login`
- [ ] Visiting `/expenses/<id>/edit` for an expense you own shows a
      form pre-filled with its current amount, category, date, and
      description
- [ ] Visiting `/expenses/<id>/edit` for an expense that does not
      exist, or belongs to another user, redirects to `/profile`
      without revealing which case it was
- [ ] Submitting the form with valid changes updates the existing
      row (not a new row) and redirects to `/profile`
- [ ] The updated values appear in the profile page's recent
      transactions, total spent, and category breakdown
- [ ] Submitting with a missing/zero/negative amount re-renders the
      form with a clear error and the row is not updated
- [ ] Submitting with an invalid or missing date re-renders the form
      with a clear error and the row is not updated
- [ ] `description` can be cleared to blank and the update still
      saves
- [ ] Each row in the profile page's recent-transactions list has a
      visible "Edit" link that reaches the correct expense's form
- [ ] `python app.py` runs with no errors and the new route matches
      the existing design system (fonts, colors, spacing via CSS
      variables)
