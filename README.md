# Expense Tracker

A web-based expense tracking application built with Python Flask and HTML, CSS, and JavaScript.

## Features
- User registration and login
- Add and manage expense records
- Dashboard and expense summaries
- Expense reports with category/date filtering
- CSV/PDF report export (where implemented in the application)

## Project structure
- `backend/` — Flask application, configuration, utilities, and Python requirements
- `frontend/` — HTML pages and frontend static assets
- `IMG/` — project images/assets
- `Query.txt` — SQL schema/setup queries

## Setup
1. Install Python 3.
2. Open a terminal in the `backend` folder.
3. Create and activate a virtual environment:
   - Windows: `py -m venv .venv` then `.venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Set the `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `SECRET_KEY` environment variables for your local setup. Do not commit real credentials.
6. Run the Flask application using the entry point documented in `backend/app.py`.

## Notes
- Do not commit `.env` files, passwords, API keys, session files, virtual environments, or personal data.
- The original runtime/session cache and local expense CSV were excluded from this GitHub-ready package.
