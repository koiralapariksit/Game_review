#!/usr/bin/env bash
set -e

# Wait for PostgreSQL if configured
if [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" == *"postgres"* ]]; then
  echo "Waiting for PostgreSQL database connection..."
  until python -c "
import sys, os, dj_database_url, psycopg2
db_info = dj_database_url.parse(os.environ['DATABASE_URL'])
try:
    conn = psycopg2.connect(
        dbname=db_info['NAME'],
        user=db_info['USER'],
        password=db_info['PASSWORD'],
        host=db_info['HOST'],
        port=db_info['PORT']
    )
    conn.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
"; do
    echo "Postgres is unavailable - sleeping 1s"
    sleep 1
  done
  echo "PostgreSQL is ready."
fi

# Execute database migrations and collect static files if running as web service
if [ "$1" = "web" ]; then
  echo "Running database migrations..."
  python manage.py migrate --noinput

  echo "Collecting static files for WhiteNoise..."
  python manage.py collectstatic --noinput

  echo "Starting Gunicorn WSGI server..."
  exec gunicorn culer.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --threads 2 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -

elif [ "$1" = "worker" ]; then
  echo "Starting Celery Worker..."
  exec celery -A culer worker -l info --concurrency=2

elif [ "$1" = "beat" ]; then
  echo "Starting Celery Beat Scheduler..."
  exec celery -A culer beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

else
  exec "$@"
fi

