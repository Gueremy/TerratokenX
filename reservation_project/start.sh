#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "--- START RUNTIME SCRIPT ---"

# Step 1: Run migrations (at runtime to ensure they hit the persistent DB)
echo "Running migrations in runtime environment..."
python manage.py migrate --no-input

# Step 2: Start Gunicorn
echo "Starting Gunicorn..."
gunicorn reservation_project.wsgi:application

echo "--- RUNTIME SCRIPT FINISHED ---"
