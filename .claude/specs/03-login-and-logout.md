# Spec: Login and Logout

## Overview

Implement session-based login and logout so registered users can authenticate and access the app. The existing `/login` route only renders a static template, and `/logout` returns a placeholder string. This step wires up a `POST /login` handler that verifies credentials against the database, stores the user's identity in a Flask session, and redirects to `/profile`. The `/logout` route clears the session and redirects to the landing page. The navbar in `base.html` is updated to show context-aware links — "Sign in / Get started" when logged out, and the user's name with a logout link when logged in.

## Depends on

- Step 1 — Database Setup (`users` table, `get_db()`)
- Step 2 — Registration (users must exist to log in)

## Routes

- `GET /login` — render login form — public *(already exists, no change)*
- `POST /login` — validate credentials, set session, redirect — public
- `GET /logout` — clear session, redirect to landing — logged-in

## Database changes

No database changes. The `users` table already has `email` and `password_hash`.

## Templates

- **Modify:** `templates/base.html`
  - Navbar: when `session.user_id` is set, show user name and a "Log out" link instead of "Sign in" and "Get started"
  - Use `{% if session.get('user_id') %}` to branch

- **Modify:** `templates/login.html`
  - No structural changes needed — form, error block, and inputs are already present

## Files to change

- `app.py`
  - Add `session` to Flask imports
  - Add `check_password_hash` to werkzeug imports
  - Set `app.secret_key` (use a hard-coded dev string for now; noted as must-change for production)
  - Convert `/login` to accept `GET` and `POST`
  - Implement `/logout` to clear session and redirect

- `templates/base.html`
  - Update `.nav-links` to branch on session state

## Files to create

None.

## New dependencies

No new dependencies. Uses:
- `flask.session` (built-in)
- `werkzeug.security.check_password_hash` (already installed)

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords verified with `werkzeug.security.check_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Store only `user_id` and `user_name` in the session — never store `password_hash`
- On invalid credentials: render `login.html` with a generic `error` variable — do not reveal whether the email exists
- On successful login: `redirect(url_for("profile"))`
- On logout: `session.clear()` then `redirect(url_for("landing"))`
- `app.secret_key` must be set before any session use; use a fixed dev string, add a comment that it must be replaced with an env var in production

## Definition of done

- [ ] `GET /login` still renders the form (200)
- [ ] Submitting valid credentials sets the session and redirects to `/profile`
- [ ] Submitting wrong password shows a generic error and does not set session
- [ ] Submitting unknown email shows the same generic error
- [ ] Submitting blank fields shows "All fields are required" error
- [ ] Visiting `/logout` clears the session and redirects to `/`
- [ ] After logout, revisiting `/login` shows no session data
- [ ] Navbar shows "Sign in / Get started" when logged out
- [ ] Navbar shows user's name and "Log out" link when logged in
- [ ] App starts without errors (`python app.py`)
