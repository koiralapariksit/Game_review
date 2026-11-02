# FC Barcelona AI Football Intelligence Platform — Deployment Guide

This document outlines the step-by-step procedures for local development, background automation, and production container orchestration.

---

## 1. Local Development Setup

### Prerequisites
- Python 3.11+
- Redis (optional for local synchronous testing via eager mode)
- Git

### Initializing Environment
```bash
# Clone the repository
git clone https://github.com/koiralapariksit/Game_review.git
cd Game_review

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create local superuser
python manage.py createsuperuser
```

### Environment Variables (`.env`)
Create a `.env` file in the project root:
```ini
DEBUG=True
SECRET_KEY=your-secure-django-secret-key
ALLOWED_HOSTS=127.0.0.1,localhost

# External Football Data Providers (Zero-Paid-API)
FOOTBALL_DATA_API_KEY=your_free_football_data_org_key
API_FOOTBALL_KEY=your_free_api_sports_key

# OpenRouter Free LLM API Key (Zero-Paid-AI)
OPENROUTER_API_KEY=your_openrouter_api_key

# Redis & Celery
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/1
CELERY_TASK_ALWAYS_EAGER=False
```

---

## 2. Obtaining Free API Keys

### `football-data.org`
1. Register for free at [https://www.football-data.org/client/register](https://www.football-data.org/client/register).
2. The free tier allows **10 requests per minute**. The client enforces sliding-window rate limiting automatically.
3. Add token as `FOOTBALL_DATA_API_KEY`.

### `OpenRouter` (`:free` Models)
1. Sign up at [https://openrouter.ai/](https://openrouter.ai/).
2. Create an API key in your dashboard.
3. The platform strictly targets `:free` endpoints (`meta-llama/llama-3.3-70b-instruct:free`, `deepseek/deepseek-r1:free`, `qwen/qwen-2.5-72b-instruct:free`) with zero cost ($0.00000).
4. Add key as `OPENROUTER_API_KEY`.

---

## 3. Manual Ingestion & Data Synchronization

To sync data manually without waiting for Celery Beat timers:

```bash
# Sync FC Barcelona fixtures & match results
python manage.py sync_football_data --fixtures

# Sync official first-team squad
python manage.py sync_football_data --squad

# Sync a specific match details by provider ID
python manage.py sync_football_data --match-id 498321
```

---

## 4. Production Deployment via Docker Compose

The production stack orchestrates 5 coordinated services:
1. `db`: PostgreSQL 16 Alpine
2. `redis`: Redis 7 Alpine
3. `web`: Gunicorn WSGI web server running WhiteNoise
4. `worker`: Celery worker handling background ingestion & AI synthesis
5. `beat`: Celery Beat database scheduler

### Running the Production Stack
```bash
# Build and start all 5 services in detached mode
docker compose up -d --build

# View real-time container logs
docker compose logs -f web worker

# Verify health status
docker compose ps
curl http://localhost:8000/healthz/
```

---

## 5. Database Backup & Disaster Recovery

### PostgreSQL Backup (`pg_dump`)
```bash
docker compose exec db pg_dump -U culer_user -d culer_db -F c -b -v -f /tmp/culer_backup.dump
docker compose cp db:/tmp/culer_backup.dump ./backups/culer_backup_$(date +%Y%m%d).dump
```

### PostgreSQL Restore (`pg_restore`)
```bash
docker compose cp ./backups/culer_backup_20261102.dump db:/tmp/restore.dump
docker compose exec db pg_restore -U culer_user -d culer_db -v --clean /tmp/restore.dump
```

---

## 6. WhiteNoise & Static Asset Delivery
Static assets are served directly through Gunicorn using WhiteNoise `CompressedManifestStaticFilesStorage`:
- Cached with immutable cache-control headers (`max-age=31536000`).
- Pre-compressed with Brotli and Gzip during `collectstatic`.

