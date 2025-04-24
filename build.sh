#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run database migrations
flask db upgrade
flask set-super-admin pp364598@gmail.com

echo "Build script finished."