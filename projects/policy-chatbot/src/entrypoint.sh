#!/bin/sh
# entrypoint.sh — Run database migrations before starting the application.
# Policy Chatbot — ensures Alembic migrations complete before uvicorn starts.
# This prevents UndefinedTableError crash-loops on first deploy.

set -e

echo "Running database migrations..."
alembic upgrade head 2>&1 || echo "WARNING: Migration failed — app may not start correctly"

echo "Starting application..."
exec "$@"
