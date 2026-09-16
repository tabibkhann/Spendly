# Spec: Date Filter For Profile Page

## Overview

Add a date-range filter to the `/profile` page so the logged-in user can narrow the financial summary (total spent, transaction count, recent transactions, category breakdown) to a specific time window instead of always seeing all-time totals. The filter is expressed entirely through query parameters on the existing `GET /profile` route, so the page stays a single URL that can be bookmarked or shared. This builds directly on the profile page shipped in Steps 4–5 and prepares the query-filtering pattern that the future expenses list (Steps 7–9) will reuse.

## Depends on

- Step 1 — Database Setup (`expenses` table, `get_db()`)
- Step 3 — Login and Logout (session with `user_id`)
- Step 4 — Profile Page Design (`templates/profile.html`, `static/css/profile.css`)
- Step 5 — Profile Backend Route (`database/queries.py` helpers, `profile()` route)

## Routes

- `GET /profile` — modify existing route — logged-in only
  - New optional query params:
    - `range` — one of `all`, `this-month`, `last-month`, `last-30-days`, `custom` (default `all`)
    - `start` — `YYYY-MM-DD`, required only when `range=custom`
    - `end` — `YYYY-MM-DD`, required only when `range=custom`
  - Invalid or malformed params fall back to `range=all` rather than erroring

## Database changes

No schema changes. Existing `expenses.date` column (stored as `YYYY-MM-DD` text) is used for range filtering with `date BETWEEN ? AND ?`.

## Templates

- **Modify:** `templates/profile.html`
  - Add a filter bar above the stats row: a `<form method="get">` with a `<select name="range">` (All time / This month / Last month / Last 30 days / Custom range) and two `<input type="date">` fields (`start`, `end`) that are only meaningfully used when "Custom range" is selected
  - Selected range and dates are reflected back into the form controls (`selected`/`value`) so the filter persists across reloads
  - Stats row, recent transactions, and category breakdown render whatever the backend already filtered — no client-side filtering logic

## Files to change

- `app.py`
  - `profile()` — read `range`, `start`, `end` from `request.args`, resolve them to a concrete `(start_date, end_date)` pair (or `None, None` for "all"), pass the resolved range + the raw `range` value to the query helpers and to the template for re-rendering the form state
- `database/queries.py`
  - `get_summary_stats(user_id, start_date=None, end_date=None)`
  - `get_recent_transactions(user_id, start_date=None, end_date=None, limit=10)`
  - `get_category_breakdown(user_id, start_date=None, end_date=None)`
  - Each adds an optional `AND date BETWEEN ? AND ?` clause (parameterised) only when both dates are provided
- `static/css/profile.css`
  - Add styles for the new filter bar (layout, select/date input styling using existing CSS variables)

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with werkzeug (no changes here, but follow the rule)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Reuse the existing `login_required` decorator — do not duplicate auth logic
- Date range resolution (`this-month`, `last-month`, `last-30-days`) happens server-side in `app.py`, not in the template
- Custom range: if `start` is after `end`, or either is missing/unparseable, silently fall back to `range=all`
- Never trust `request.args` values directly in SQL — always pass through `?` placeholders

## Definition of done

- [ ] Visiting `/profile` with no query params behaves exactly as before (all-time totals)
- [ ] Visiting `/profile?range=this-month` shows only expenses dated within the current calendar month
- [ ] Visiting `/profile?range=last-month` shows only expenses dated within the previous calendar month
- [ ] Visiting `/profile?range=last-30-days` shows only expenses from the last 30 days up to today
- [ ] Visiting `/profile?range=custom&start=2026-08-01&end=2026-08-15` shows only expenses in that inclusive date range
- [ ] An invalid custom range (e.g. `start` after `end`, or missing dates) falls back to all-time results without a 500 error
- [ ] Total spent, transaction count, recent transactions, and category breakdown are all consistent with the selected range
- [ ] Filter form shows the currently active range/dates after page reload
- [ ] Page uses only CSS variables for colours — no hardcoded hex values
- [ ] App starts without errors (`python app.py`)
- [ ] All other existing routes still work (no regressions)
