#!/bin/bash
set -e

# Wait for the database to be ready
echo "Waiting for database to be ready..."
until PGPASSWORD=$PGPASSWORD psql -h $PGHOST -U $PGUSER -d $PGDATABASE -c '\q'; do
  echo "Database is unavailable - sleeping"
  sleep 1
done

echo "Database is up - executing migrations"

# Run database migrations
python database_check.py
python migration_add_dlp_columns.py
python migration_add_local_llm_columns.py
python migration_pattern_levels.py

# Start Streamlit
echo "Starting Streamlit application..."
streamlit run app.py