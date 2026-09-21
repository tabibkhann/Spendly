# Spec: Add Expense

## Overview
This feature implements the "Add Expense" flow, replacing the
`/expenses/add` placeholder in `app.py`. It lets a logged-in user
record a new expense (amount, category, date, optional description)
via a form, persisting it to the `expenses` table so it immediately
appears in the profile page's stats, recent transactions, and
category breakdown. This is the first of the three CRUD steps
(add/edit/delete) that make the tracker actually useful.

## Depends on
- Step 1 — `database/db.py` (schema: `expenses` table)
- Step 3 — Login/logout (session-based auth)
- Step 5 — Profile backend route (`get_user_by_id`, stats/query helpers)

## Routes
- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert a new expense, then
  redirect to `/profile` — logged-in only

## Database changes
No database changes. The existing `expenses` table
(`database/db.py`) already has the required columns:
`user_id, amount, category, date, description, created_at`.

## Templates
- **Create:** `templates/add_expense.html` — form with fields for
  amount, category (select), date, description; extends `base.html`;
  follows the `auth-section` / `form-group` / `form-input` /
  `btn-submit` markup pattern used in `register.html` and `login.html`,
  with an `auth-error`-style block for validation errors.
- **Modify:** `templates/profile.html` — add a link/button
  (`<a href="{{ url_for('add_expense') }}">`) to reach the new form,
  e.g. near the recent-transactions or summary section.

## Files to change
- `app.py` — replace the `add_expense` placeholder route with
  `GET`/`POST` handling, `@login_required`, form validation, and
  insert logic (either inline `get_db()` calls matching the
  `register`/`login` style, or a new helper in `database/queries.py`
  — implementer's choice, but stay consistent with existing style).
- `templates/profile.html` — add the entry point link to the form.

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (n/a to this feature, but no new
  auth code should deviate from this)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate on the server: `amount` must be a positive number,
  `category` must be non-empty, `date` must be a valid `YYYY-MM-DD`
  date, `description` is optional. Re-render the form with an error
  message (matching the `error` pattern from `register`/`login`) on
  invalid input — do not lose the user's other entered values.
- Category options should match the categories already used in
  `seed_db()` (Food, Transport, Bills, Health, Entertainment,
  Shopping, Other) so the category breakdown stays consistent.
- New expenses must always be attached to `session["user_id"]` —
  never trust a client-supplied user id.
- On success, redirect (`302`) to `/profile`, not render directly,
  so a page refresh doesn't resubmit the form.

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in shows a form with
      amount, category, date, and description fields
- [ ] Submitting the form with a valid amount/category/date creates
      a new row in `expenses` for the current user and redirects to
      `/profile`
- [ ] The new expense appears in the profile page's recent
      transactions, total spent, and category breakdown
- [ ] Submitting with a missing/zero/negative amount re-renders the
      form with a clear error and no row is inserted
- [ ] Submitting with an invalid or missing date re-renders the form
      with a clear error and no row is inserted
- [ ] `description` can be left blank and the expense still saves
- [ ] The form is reachable from `/profile` via a visible link/button
- [ ] `python app.py` runs with no errors and the new route matches
      the existing design system (fonts, colors, spacing via CSS
      variables)
