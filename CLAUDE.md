# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run development server (http://localhost:5001)
python app.py

# Run tests
pytest
```

No build step — static assets are served directly by Flask.

## Architecture

This is **Spendly**, a Flask expense-tracker app. It uses Jinja2 templates, vanilla CSS/JS, and SQLite (not yet wired up).

**Entry point**: `app.py` — all routes are defined here. The app runs on port 5001.

**Database layer**: `database/db.py` — stub file. Will expose `get_db()`, `init_db()`, and `seed_db()`. Uses SQLite with `row_factory` and foreign keys enabled.

**Templates** extend `base.html` via Jinja2 block inheritance (`title`, `content`, `scripts`). Use `url_for()` for all internal links.

**Static assets**: `static/css/style.css` defines the full design system (CSS custom properties for colors, typography, spacing). `static/css/landing.css` adds landing-page-only styles. `static/js/main.js` is a placeholder.

**Design tokens** (defined in `style.css :root`):
- Colors: `--accent` (dark green `#1a472a`), `--accent-2` (gold `#c17f24`), `--danger` (red)
- Typography: `--font-display` (DM Serif Display), `--font-body` (DM Sans)
- Layout: `--max-width: 1200px`, `--auth-width: 440px`
- Radii: `--radius-sm/md/lg` (6/12/20px)

**Planned route roadmap** (numbered steps in comments):
- Step 1: `database/db.py` — SQLite setup
- Step 3: `/logout`
- Step 4: `/profile`
- Steps 7–9: `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`

The GitHub remote is `https://github.com/tabibkhann/Spendly.git`.
