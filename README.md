# Expense Tracker with Analytics

Private income and expense tracking with monthly summaries and category charts.

This is a fresh implementation based on the project description in Ravi Kumar's resume. It does not claim to recover an earlier codebase or demonstrate past production usage.

## Run locally

Requires Python 3.11+. From this repository:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m flask --app app run --port 5000
```

Open http://localhost:5000. Set configuration as environment variables; `.env.example` documents the available values. Flask does not automatically load `.env` unless python-dotenv is installed. For persistent sessions set SECRET_KEY to a random secret. SQLite data is created automatically in `instance/app.db`. To reset local data, stop the server and remove that database.

## Verify

```sh
python -m pytest -q
python -m ruff check .
```

## Docker

```sh
docker build -t expense-tracker-analytics .
docker run --rm -p 5000:5000 -e SECRET_KEY=your-random-secret -v expense-tracker-analytics-data:/app/instance expense-tracker-analytics
```

The image serves with Waitress as a non-root user. Check volume ownership if using a host directory. `/api/health` returns a health check. Never commit `.env`, database files or credentials.

## Deployment boundaries

This is a portfolio application. Before public deployment, use HTTPS, set COOKIE_SECURE=true for cookie apps, configure a persistent database and SECRET_KEY, add authentication rate limiting, monitoring and backups, and review access rules. No default account or password is shipped. CI is configured to run lint and tests on pushes and pull requests.

## Features and API

Create your own account from the sign-in page. Every transaction and summary is scoped to the signed-in user. Amounts use integer paise in SQLite, with Decimal validation at the API boundary; currency is INR. Monthly filtering uses ISO date ranges and an index on owner/date. Transactions support create, edit, delete and pagination. Chart.js 4.4.8 loads from jsDelivr; category totals remain available when offline.

GET /api/session supplies the CSRF token; send it as X-CSRF-Token for mutations. POST /api/register, /api/login and /api/logout manage sessions. GET /api/transactions?month=YYYY-MM&page=1&limit=20 lists records. POST /api/transactions creates a record; PUT/DELETE /api/transactions/id edits/removes it. A transaction JSON object has kind (income/expense), amount (decimal string), category, note and occurred_on (YYYY-MM-DD). GET /api/summary?month=YYYY-MM returns totals in paise and expense category totals. Errors use an `error` field.
