# Spec: Registration

## Overview

Implement user registration so new visitors can create a Spendly account. The existing `/register` route only renders a static template — this step wires up a `POST` handler that validates the submitted form, hashes the password with werkzeug, inserts a new row into the `users` table, and redirects the user to the login page on success. This is the first step that writes user data and establishes the pattern for all future form-handling routes.

## Depends on

- Step 1 — Database Setup (`database/db.py`, `users` table, `get_db()`)

## Routes

- `GET /register` — render registration form — public *(already exists, no change)*
- `POST /register` — process registration form submission — public

## Database changes

No database changes. The `users` table created in Step 1 already has all required columns: `name`, `email` (UNIQUE), `password_hash`, `created_at`.

## Templates

- **Modify:** `templates/register.html`
  - Wrap existing markup in a `<form method="POST" action="/register">`
  - Add `name` input (text, required)
  - Add `email` input (email, required)
  - Add `password` input (password, required)
  - Add `confirm_password` input (password, required)
  - Add error display block (show `error` variable when present, styled with `--danger`)
  - Preserve all existing design — only add functional form elements

## Files to change

- `app.py` — convert `/register` to handle GET + POST; add import for `redirect`, `url_for`, `request`, `flash`
- `templates/register.html` — add form markup and error display

## Files to create

None.

## New dependencies

No new dependencies. Uses:
- `werkzeug.security.generate_password_hash` (already installed)
- `sqlite3` UNIQUE constraint for duplicate email detection (already in schema)
- Flask built-ins: `request`, `redirect`, `url_for`

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate server-side: all fields required, passwords must match, email must be unique
- On duplicate email: catch `sqlite3.IntegrityError` and show a user-friendly message
- On success: `redirect(url_for("login"))` — do not log the user in automatically (session handled in Step 3)
- Pass errors back to the template via a template variable (`error`), not Flask flash

## Definition of done

- [ ] Visiting `/register` renders the form (GET still works)
- [ ] Submitting with all valid fields creates a new row in `users`
- [ ] The stored `password_hash` is a werkzeug hash string, not plaintext
- [ ] Submitting with mismatched passwords shows an error and does not insert
- [ ] Submitting with a duplicate email shows an error and does not insert
- [ ] Submitting with any blank field shows an error and does not insert
- [ ] On success, user is redirected to `/login`
- [ ] App starts without errors (`python app.py`)
