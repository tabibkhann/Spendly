# Spec: Delete Expense

## Overview
This feature implements the "Delete Expense" flow, replacing the
`/expenses/<id>/delete` placeholder in `app.py`. It lets a logged-in
user permanently remove an expense they own directly from the
profile page, with a confirmation prompt to guard against accidental
clicks. This is the third and final CRUD step (add/edit/delete),
completing the core expense-management functionality of Spendly.

## Depends on
- Step 1 — `database/db.py` (schema: `expenses` table)
- Step 3 — Login/logout (session-based auth)
- Step 5 — Profile backend route (`get_user_by_id`, stats/query helpers)
- Step 7 — Add Expense (`EXPENSE_CATEGORIES`, validation/route pattern)
- Step 8 — Edit Expense (`get_expense_by_id`, ownership-check pattern,
  `id` already added to `get_recent_transactions`, per-row action link
  in `profile.html`)

## Routes
- `POST /expenses/<int:id>/delete` — delete the expense, then redirect
  to `/profile` — logged-in only, owner only

No `GET` route. A confirmation dialog happens client-side (via a
`confirm()` prompt on submit) before the `POST` is ever sent — there is
no separate "are you sure" page.

If `id` does not exist, or exists but belongs to a different user,
redirect to `/profile` without deleting anything and without revealing
which case it was (same behavior as Step 8's edit-ownership check).

## Database changes
No schema changes. The existing `expenses` table
(`database/db.py`) is sufficient for a `DELETE` scoped by `id` and
`user_id`.

## Templates
- **Modify:** `templates/profile.html` — add a "Delete" action next to
  the existing "Edit" pencil link on each recent-transaction row: a
  small inline `<form method="POST" action="{{ url_for('delete_expense',
  id=tx.id) }}">` containing a single icon button, with
  `onsubmit="return confirm('Delete this expense?')"` on the form to
  prevent accidental submission.

## Files to change
- `app.py` — replace the `delete_expense` placeholder route with a
  `POST`-only handler: `@login_required`, ownership check via
  `get_expense_by_id` (redirect to `/profile` if `None`, mirroring
  Step 8), then delete and redirect.
- `database/queries.py` — add `delete_expense(expense_id, user_id)`,
  a parameterised `DELETE FROM expenses WHERE id = ? AND user_id = ?`,
  scoped by `user_id` exactly like `update_expense` (never trust the
  id alone).
- `templates/profile.html` — add the per-row delete form/button.
- `static/css/profile.css` — any small additions needed to style the
  new delete icon button consistent with the existing edit icon link.

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (n/a to this feature, but no new
  auth code should deviate from this)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html` (n/a here since no new template is
  created, but the modified `profile.html` already does)
- Every DB lookup and delete for a specific expense must filter by
  both `id` AND `session["user_id"]` — a user must never be able to
  delete another user's expense by guessing or editing the URL's id
  (IDOR protection), and the "not found" vs "not yours" cases must be
  indistinguishable to the client.
- The delete action must be triggered by `POST`, never `GET` — a
  `GET` request (e.g. a browser prefetch, a link crawler) must never
  delete data.
- Require a client-side confirmation (`confirm()`) before the delete
  form submits, so a stray click doesn't destroy data with no warning.
- On success, redirect (`302`) to `/profile`.

## Definition of done
- [ ] Visiting `/expenses/<id>/delete` with `GET` does not delete
      anything (method not allowed)
- [ ] Submitting the delete form while logged out redirects to
      `/login` and does not delete anything
- [ ] Clicking "Delete" on a transaction you own shows a confirmation
      prompt before anything happens
- [ ] Confirming deletion removes the expense and redirects to
      `/profile`
- [ ] Cancelling the confirmation prompt leaves the expense untouched
- [ ] The deleted expense no longer appears in recent transactions,
      and total spent / transaction count / category breakdown update
      accordingly
- [ ] Submitting a delete for an expense id that does not exist, or
      belongs to another user, redirects to `/profile` without
      deleting anything and without revealing which case it was
- [ ] Each row in the profile page's recent-transactions list has a
      visible "Delete" action alongside the existing "Edit" action
- [ ] `python app.py` runs with no errors and the delete control
      matches the existing design system (fonts, colors, spacing via
      CSS variables)
