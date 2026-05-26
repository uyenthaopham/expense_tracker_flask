# Expense Tracker – Deployment Runbook

> **Target setup time:** < 5 minutes (from `git clone` to first browser hit)  
> **Audience:** Developers, DevOps, On-call engineers  
> **Last updated:** 2026-05

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quick Start (< 5 min)](#2-quick-start--5-min)
3. [Environment Variables Reference](#3-environment-variables-reference)
4. [Running Tests Locally](#4-running-tests-locally)
5. [Running Tests in Docker](#5-running-tests-in-docker)
6. [CI Pipeline Overview](#6-ci-pipeline-overview)
7. [Database Migrations](#7-database-migrations)
8. [Zero-Downtime Re-Deployment](#8-zero-downtime-re-deployment)
9. [Rollback Procedure](#9-rollback-procedure)
10. [Health Checks & Monitoring](#10-health-checks--monitoring)
11. [Troubleshooting](#11-troubleshooting)
12. [Security Checklist](#12-security-checklist)

---

## 1. Prerequisites

| Tool | Minimum Version | Install |
|------|----------------|---------|
| Docker | 24.x | https://docs.docker.com/get-docker/ |
| Docker Compose | v2.x (plugin) | bundled with Docker Desktop |
| Git | 2.x | https://git-scm.com/ |
| make (optional) | any | package manager |

Verify:
```bash
docker --version          # Docker version 24.x.x
docker compose version    # Docker Compose version v2.x.x
```

---

## 2. Quick Start (< 5 min)

```bash
# 1. Clone
git clone https://github.com/uyenthaopham/expense_tracker_flask.git
cd expense_tracker_flask

# 2. Copy DevOps files into the project root
#    (copy all files from this package next to run.py)

# 3. Configure environment (30 seconds)
cp .env.example .env
# Edit .env – set SECRET_KEY and POSTGRES_PASSWORD at minimum:
#   SECRET_KEY=<random 32+ char string>
#   POSTGRES_PASSWORD=<your password>

# 4. Start all services
docker compose up -d

# 5. Run database migrations
docker compose exec app flask db upgrade

# 6. Open browser
open http://localhost      # or http://localhost:80
```

**Done.** The app is running behind Nginx on port 80.

---

## 3. Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ | — | Flask session signing key (use ≥ 32 random chars) |
| `POSTGRES_PASSWORD` | ✅ | — | PostgreSQL password |
| `POSTGRES_DB` | ❌ | `expense_tracker` | Database name |
| `POSTGRES_USER` | ❌ | `expense_user` | Database user |
| `FLASK_ENV` | ❌ | `production` | `development` \| `production` \| `testing` |
| `DATABASE_URL` | ❌ | constructed from POSTGRES_* | Override for external DB |

Generate a secure SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 4. Running Tests Locally

### Setup (one-time)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Run all tests

```bash
pytest                             # uses pytest.ini defaults (coverage gate included)
```

### Useful test commands

```bash
# Quick run, no coverage (fastest feedback)
pytest -x --no-cov

# Only authentication tests
pytest tests/test_auth.py -v

# Only security-tagged tests
pytest -m security -v

# Show 10 slowest tests
pytest --durations=10

# Watch mode (re-runs on file save)
ptw tests/                         # requires pytest-watch
```

### Expected output

```
========================= test session starts ==========================
collected 56 items

tests/test_auth.py::TestRegistration::test_register_success PASSED
tests/test_auth.py::TestRegistration::test_register_duplicate_email PASSED
...
tests/test_expenses.py::TestTransactionIntegrity::test_expense_persists PASSED

---------- coverage: platform linux, python 3.11 ----------
Name                    Stmts   Miss  Cover
-------------------------------------------
app/__init__.py            35      2    94%
app/models.py              68      4    94%
app/auth/routes.py         82      8    90%
app/expense/routes.py     104     12    88%
app/category/routes.py     46      5    89%
-------------------------------------------
TOTAL                     335     31    91%    ← must be ≥ 85%

==================== 56 passed in 4.83s ====================
```

---

## 5. Running Tests in Docker

Tests run against a real PostgreSQL instance (same as production):

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm test
```

Or just the linter:
```bash
docker compose run --rm app flake8 app/ tests/
```

---

## 6. CI Pipeline Overview

```
Push / PR
    │
    ▼
┌───────────┐
│   lint    │  flake8 · black --check · isort --check · bandit
└─────┬─────┘
      │ (parallel)
  ┌───┴────┐    ┌──────────┐
  │  test  │    │ security │
  │ pytest │    │  safety  │
  │ ≥ 85%  │    │  check   │
  └───┬────┘    └────┬─────┘
      └──────┬────────┘
             ▼
      ┌─────────────┐
      │ build-check │  docker compose build + smoke test
      └──────┬──────┘
             │  (only on PR to main)
             ▼
      ┌─────────────┐
      │    gate     │  ✅ PR can merge to main
      └─────────────┘
```

**Branch protection rules to configure in GitHub:**
1. Go to **Settings → Branches → Add rule** for `main`
2. Enable **Require status checks to pass before merging**
3. Add required checks: `lint`, `test`, `security`, `build-check`, `gate`
4. Enable **Require branches to be up to date before merging**
5. Enable **Require linear history** (optional but recommended)

---

## 7. Database Migrations

### Apply pending migrations

```bash
docker compose exec app flask db upgrade
```

### Create a new migration (after model changes)

```bash
# 1. Make changes to app/models.py
# 2. Generate migration
docker compose exec app flask db migrate -m "add_column_expense_date"
# 3. Review the generated file in migrations/versions/
# 4. Apply it
docker compose exec app flask db upgrade
```

### Rollback last migration

```bash
docker compose exec app flask db downgrade
```

### Show migration history

```bash
docker compose exec app flask db history
docker compose exec app flask db current
```

---

## 8. Zero-Downtime Re-Deployment

```bash
# 1. Pull latest code
git pull origin main

# 2. Build new image (without stopping the running app)
docker compose build app

# 3. Apply DB migrations before switching traffic
docker compose exec app flask db upgrade

# 4. Recreate only the app container (Nginx keeps serving)
docker compose up -d --no-deps app

# 5. Verify the new container is healthy
docker compose ps
docker compose logs app --tail=50
```

---

## 9. Rollback Procedure

### Option A – Roll back to previous Docker image tag

```bash
# Tag images during build in CI (recommended):
#   docker build -t expense-app:$GITHUB_SHA .

# Rollback:
docker compose stop app
docker tag expense-app:<previous-sha> expense-app:latest
docker compose up -d app
docker compose exec app flask db downgrade   # if migration was applied
```

### Option B – Git revert + redeploy

```bash
git revert HEAD --no-edit
git push origin main
# CI pipeline runs automatically; re-deploy after green
```

---

## 10. Health Checks & Monitoring

### Container status

```bash
docker compose ps                    # all services + health status
docker compose logs -f app           # live app logs
docker compose logs -f nginx         # live nginx logs
docker stats                         # CPU / memory usage
```

### Manual health probe

```bash
curl -v http://localhost/            # expects HTTP 200
curl -v http://localhost/health      # nginx health endpoint
```

### Database connectivity

```bash
docker compose exec db psql \
  -U expense_user -d expense_tracker \
  -c "SELECT COUNT(*) FROM \"user\";"
```

---

## 11. Troubleshooting

### App container crashes immediately

```bash
docker compose logs app
# Common causes:
#   - SECRET_KEY not set → check .env
#   - Database not reachable → check db healthcheck
#   - Migration pending → run flask db upgrade
```

### Port 80 already in use

```bash
# Option 1: find and stop the conflicting process
sudo lsof -i :80

# Option 2: change the host port in docker-compose.yml
#   ports: ["8080:80"]
```

### Tests fail with "ModuleNotFoundError: app"

```bash
# Ensure you're running pytest from the project root
cd expense_tracker_flask
FLASK_APP=run.py pytest
```

### Coverage below 85%

```bash
# See which lines are not covered
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Database migration conflict

```bash
# List heads (multiple heads = conflict)
docker compose exec app flask db heads

# Merge heads
docker compose exec app flask db merge heads -m "merge_heads"
docker compose exec app flask db upgrade
```

---

## 12. Security Checklist

Before deploying to production, verify:

- [ ] `SECRET_KEY` is a long random string (≥ 32 chars), not the default
- [ ] `POSTGRES_PASSWORD` is strong and unique
- [ ] `.env` is in `.gitignore` (never committed)
- [ ] `FLASK_ENV=production` (disables debug mode)
- [ ] HTTPS is configured (add TLS cert to Nginx)
- [ ] `safety check` passes (no known CVEs in dependencies)
- [ ] `bandit` scan passes (no high-severity findings)
- [ ] Database is not exposed on a public port (only internal `backend` network)
- [ ] Nginx rate limiting configured for auth endpoints (optional)
- [ ] Regular dependency updates scheduled (Dependabot or weekly `safety` run)
