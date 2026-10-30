#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

# Install python dependencies
pip install -r requirements.txt

# Collect static files (CSS, JS, images)
python manage.py collectstatic --noinput

# Run database migrations
python manage.py migrate

# Seed initial bank accounts, demo users, loan products and billers
python manage.py seed_demo_data
