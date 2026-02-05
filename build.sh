#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "--- START BUILD SCRIPT ---"

# Step 1: Install dependencies
# We use the requirements.txt from the reservation_project folder
pip install -r reservation_project/requirements.txt

# Step 2: Prepare environment
cd reservation_project
mkdir -p staticfiles
mkdir -p data

# Step 3: Database operations
echo "Running migrations..."
python manage.py migrate --no-input

echo "Checking migration status..."
python manage.py showmigrations booking

# Step 4: Static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "--- BUILD SCRIPT FINISHED ---"
