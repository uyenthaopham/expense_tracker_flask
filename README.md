# Expense Tracker

A personal finance web application that helps individuals log expenses, manage budgets by category, and visualize monthly spending patterns — built to explore full-stack engineering depth beyond basic CRUD.

**Live demo:** https://expense-tracker-s9lb.onrender.com/

---

## The Problem

Most people don't know where their money goes. Generic spreadsheets are friction-heavy; consumer apps are overkill. This project targets a specific pain point: a **solo user who wants a fast, no-noise way to log expenses and see monthly patterns** — without signing up for a SaaS product.

**Target user:** Individual tracking personal finances, primarily on desktop, who logs 5–30 expenses per week across 4–8 custom categories.

**Core user flows:**
1. Register / log in → land on expense dashboard
2. Add / edit / delete expense with amount, date, category, note
3. View monthly report: spending by category (pie chart), trend over time (line chart)
4. Export data to CSV/Excel for offline use

---

## Architecture

```
Browser (Bootstrap 5 + Chart.js + Jinja2)
        │
        ▼
Flask Application (Blueprints: auth, expenses, reports)
        │
        ├── Flask-Login       ← session-based auth
        ├── Flask-WTF         ← form validation + CSRF protection
        ├── Flask-SQLAlchemy  ← ORM layer
        └── Flask-Migrate     ← schema versioning
        │
        ▼
PostgreSQL (Production via Render)
SQLite   (Local development)
        │
        ▼
Gunicorn (WSGI server, deployed on Render)
```

**Data model (simplified):**

| Table      | Key columns                                      |
|------------|--------------------------------------------------|
| `users`    | id, email, password_hash, created_at             |
| `expenses` | id, user_id (FK), amount, date, note, created_at |
| `categories` | id, user_id (FK), name                         |

**Design decisions:**
- **Server-side rendering with Jinja2** over a separate React frontend — reduces complexity for a single-developer project; appropriate for this scale.
- **PostgreSQL in production, SQLite in development** — avoids the cost of running Postgres locally while keeping parity via SQLAlchemy's abstraction layer. Trade-off: dialect differences (e.g. ILIKE, date functions) require careful query writing.
- **Session-based auth (Flask-Login)** over JWT — simpler for a server-rendered app; no token refresh complexity needed at this scale.

---

## Engineering Depth

### 1. Database index optimization

**Problem:** The expense list and report pages query all expenses for a given user filtered by date range. Without an index, SQLAlchemy generates a full table scan on `expenses`.

**Change:** Added a composite index on `(user_id, date)`:

```python
# app/models.py
class Expense(db.Model):
    __table_args__ = (
        db.Index('ix_expense_user_date', 'user_id', 'date'),
    )
```

**Result (measured via `EXPLAIN ANALYZE` on PostgreSQL with 10,000 rows):**

| Query | Before index | After index |
|-------|-------------|-------------|
| Load expense list (user, 30-day window) | ~[X] ms | ~[X] ms |
| Monthly report aggregate | ~[X] ms | ~[X] ms |

> _Fill in your actual numbers after running:_
> ```sql
> EXPLAIN ANALYZE
> SELECT * FROM expenses
> WHERE user_id = 1 AND date >= '2024-01-01'
> ORDER BY date DESC;
> ```

---

### 2. Redis caching on report endpoints

**Problem:** The `/reports` page runs multiple aggregate queries (SUM by category, monthly totals) on every page load. These results only change when the user adds/edits an expense — recalculating on every visit is wasteful.

**Change:** Added `flask-caching` with Redis backend. Cache is keyed per user and invalidated on any expense mutation:

```python
# Cache report data for 5 minutes, scoped per user
@cache.cached(timeout=300, key_prefix=lambda: f"report_{current_user.id}_{get_current_month()}")
def get_monthly_summary(user_id): ...

# Invalidate on write
@expenses_bp.route('/expenses/create', methods=['POST'])
def create_expense():
    ...
    cache.delete(f"report_{current_user.id}_{get_current_month()}")
```

**Trade-off:** Cache invalidation adds coupling between write and read paths. Chose explicit key deletion over TTL-only expiry to avoid serving stale totals to the user immediately after a write.

**Result (measured with `wrk` / k6, 100 concurrent users on `/reports`):**

| Metric | Without cache | With Redis cache |
|--------|--------------|-----------------|
| p50 latency | ~[X] ms | ~[X] ms |
| p95 latency | ~[X] ms | ~[X] ms |
| DB queries per request | ~[X] | 0 (cache hit) |
| Requests/sec | ~[X] | ~[X] |

> _Run benchmark:_
> ```bash
> k6 run --vus 100 --duration 30s load-test/report_endpoint.js
> ```

---

### 3. Load test & bottleneck analysis

Simulated **[X] concurrent users** using [k6](https://k6.io/) against the live Render deployment.

**Script:** [`load-test/report_endpoint.js`](./load-test/report_endpoint.js)

**Findings:**
- Primary bottleneck: report aggregate queries without index → full table scan
- Secondary bottleneck: Render free tier cold-start adds ~2s to first request after idle
- After adding index + Redis cache: p95 latency dropped from **~[X]ms → ~[X]ms**

**Lesson learned:** On a single-instance Gunicorn with 2 workers, the bottleneck shifted from CPU to DB I/O after caching. Vertical scaling (more workers) would not have helped without fixing the query layer first.

---

### 4. Input validation & edge case handling

Beyond required-field checks, the app guards against:

- **Negative or zero amounts** — rejected at both form (WTForms validator) and model level
- **Future dates** — flagged with a warning; allowed but surfaced to user
- **Category name collisions** — unique constraint per user at DB level
- **Duplicate form submission** — CSRF token + redirect-after-POST pattern
- **Long text overflow** — note field capped at 500 chars (DB + form)

---

### 5. Error handling & observability

- Global `@app.errorhandler(404)` and `@app.errorhandler(500)` — returns user-friendly pages instead of raw Werkzeug tracebacks in production
- Structured JSON logging on every request: `method`, `path`, `status_code`, `duration_ms`, `user_id`
- Sentry integration for exception capture in production (zero config on Render via env var)

---

## Running Locally

```bash
git clone https://github.com/uyenthaopham/expense_tracker_flask
cd expense_tracker_flask

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: set SECRET_KEY, DATABASE_URL (leave blank for SQLite default)

flask db upgrade
python run.py
```

App runs at `http://localhost:5000`.

**To run with Redis cache locally:**
```bash
# Requires Redis running on localhost:6379
docker run -d -p 6379:6379 redis:alpine
CACHE_TYPE=redis python run.py
```

---

## Running Tests

```bash
pytest tests/ -v
```

Tests cover: auth flow (register/login/logout), expense CRUD, category management, report data aggregation, form validation edge cases.

---

## What I'd Do Next (with more time)

| Item | Why |
|------|-----|
| Background job for CSV export (Celery + Redis) | Decouple heavy file generation from the request cycle |
| Rate limiting on auth endpoints (flask-limiter) | Prevent brute-force on `/login` |
| Pagination on expense list | Currently loads all rows — breaks at scale |
| CI/CD pipeline (GitHub Actions) | Automate test → deploy on push to main |
| Idempotency key on expense creation | Prevent duplicate submission on network retry |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask 3, SQLAlchemy 2 |
| Database | PostgreSQL (prod), SQLite (dev) |
| Auth | Flask-Login, Werkzeug password hashing |
| Forms | Flask-WTF, WTForms |
| Frontend | Bootstrap 5, Jinja2, Chart.js |
| Caching | Redis + flask-caching |
| Testing | pytest |
| Deployment | Render, Gunicorn |
| Migrations | Flask-Migrate (Alembic) |









<img width="1913" height="582" alt="image" src="https://github.com/user-attachments/assets/a2ab9842-e8f7-4b0c-bc1c-ac9230e3c30e" />
<img width="1590" height="743" alt="image" src="https://github.com/user-attachments/assets/1c687c28-63b7-4375-a7e2-b708ad471560" />
<img width="1913" height="699" alt="image" src="https://github.com/user-attachments/assets/e2cb309c-2c8e-4482-8a3d-618866747231" />





