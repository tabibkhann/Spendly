# Spec: Profile Page Design

## Overview

Build the `/profile` page as the first logged-in screen in Spendly. It shows the authenticated user's account details (name, email, member since date) alongside a quick financial summary (total expenses, number of transactions, and a per-category breakdown) pulled live from the database. The page enforces authentication — unauthenticated visitors are redirected to `/login`. It also establishes the logged-in layout pattern (page header + card grid) that dashboard and expense pages will follow.

## Depends on

- Step 1 — Database Setup (`users`, `expenses` tables, `get_db()`)
- Step 3 — Login and Logout (session with `user_id` and `user_name`)

## Routes

- `GET /profile` — render profile page for the logged-in user — logged-in only

## Database changes

No database changes.

## Templates

- **Create:** `templates/profile.html`
  - Extends `base.html`
  - Page header: user's name as title, email as subtitle
  - Account card: name, email, member since (`created_at` formatted as "Month YYYY")
  - Stats row: total spent (sum of all expenses), number of transactions
  - Category breakdown: list of categories with total spent per category, sorted descending
  - Uses only existing CSS variables — no hardcoded colours

## Files to change

- `app.py`
  - Import `functools.wraps` (for auth decorator)
  - Add a `login_required` decorator that checks `session.get("user_id")` and redirects to `/login` if missing
  - Replace the `/profile` placeholder with a real handler: query user row + expense summary, pass to template

## Files to create

- `templates/profile.html` — full profile page template
- `static/css/profile.css` — page-scoped styles (card grid, stats row, category list)

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with werkzeug (no changes here, but follow the rule)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Authentication guard: use a `login_required` decorator; apply it to `/profile` (and all future protected routes)
- Never expose `password_hash` to the template — query only `id`, `name`, `email`, `created_at`
- All DB queries use `get_db()` from `database/db.py`
- `profile.css` must be linked via `{% block head %}` in `profile.html`, not added to `style.css`
- Lucide icons loaded via CDN in `base.html` (`<script src="https://unpkg.com/lucide@latest">`) and initialised with `lucide.createIcons()` in the `{% block scripts %}` of `profile.html`

## Definition of done

- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in renders the page (200)
- [ ] Page shows the correct user name and email from the database
- [ ] "Member since" shows the `created_at` date formatted as "Month YYYY"
- [ ] Total spent and transaction count reflect the logged-in user's actual expenses
- [ ] Category breakdown lists only categories that have at least one expense, sorted by total descending
- [ ] Page uses only CSS variables for colours — no hardcoded hex values
- [ ] App starts without errors (`python app.py`)
- [ ] All other existing routes still work (no regressions)
