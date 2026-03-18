#!/bin/sh
# entrypoint.sh — Run database migrations then start the application.
# Migrations are idempotent (alembic tracks applied versions).
# On first deploy, this creates all tables. On subsequent deploys, it
# applies any new migrations. If migrations fail, the app still starts
# (the /ready endpoint will report database issues).

set -e

echo "Running database migrations..."
alembic upgrade head 2>&1 || {
    echo "WARNING: Database migration failed. The app will start but may not function correctly."
    echo "Check database connectivity and run 'alembic upgrade head' manually."
}

echo "Starting application..."
exec "$@"
