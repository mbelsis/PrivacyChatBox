"""
Migration script to add local LLM configuration columns to the Settings table
"""

import os
import sys
import time
import sqlalchemy as sa
from sqlalchemy import Column, Integer, Float
from database import init_db, get_session
import traceback

def run_migration():
    """
    Add local LLM configuration columns to the Settings table
    """
    print("Starting migration to add local LLM configuration columns to the Settings table...")
    print(f"Using DATABASE_URL: {os.environ.get('DATABASE_URL', 'Not set')[:10]}...")
    
    # Initialize database with explicit timeout
    try:
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        traceback.print_exc()
        return
    
    # Get session with timeout
    try:
        session = get_session()
        print("Database session created.")
    except Exception as e:
        print(f"Error creating database session: {str(e)}")
        traceback.print_exc()
        return
    
    # Check if the database is accessible with timeout
    connection_attempt = 0
    max_attempts = 3
    
    while connection_attempt < max_attempts:
        connection_attempt += 1
        try:
            print(f"Connection attempt {connection_attempt}/{max_attempts}...")
            session.execute(sa.text("SELECT 1"))
            print("Database connection successful.")
            break
        except Exception as e:
            print(f"Error connecting to database (attempt {connection_attempt}): {str(e)}")
            if connection_attempt < max_attempts:
                print("Waiting 2 seconds before retrying...")
                time.sleep(2)
            else:
                print("Maximum connection attempts reached. Exiting.")
                session.close()
                return
    
    # Define columns to add with SQL data types (not SQLAlchemy types)
    columns_to_add = {
        "local_model_context_size": "INTEGER",
        "local_model_gpu_layers": "INTEGER",
        "local_model_temperature": "FLOAT"
    }
    
    # Direct SQL approach for getting existing columns
    try:
        # Check if table exists first
        table_check = session.execute(sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'settings')"
        ))
        table_exists = table_check.scalar()
        
        if not table_exists:
            print("Settings table does not exist. No migration needed.")
            session.close()
            return
            
        # Get existing columns
        result = session.execute(sa.text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'settings'"
        ))
        existing_columns = [row[0] for row in result]
        print(f"Existing columns: {existing_columns}")
    except Exception as e:
        print(f"Error checking existing columns: {str(e)}")
        traceback.print_exc()
        session.close()
        return
    
    # Add missing columns one by one with direct SQL
    migration_success = True
    
    for column_name, column_type in columns_to_add.items():
        if column_name not in existing_columns:
            print(f"Adding column: {column_name} ({column_type})")
            
            # Determine default value based on column name
            default_value = "2048" if column_name == "local_model_context_size" else \
                           "-1" if column_name == "local_model_gpu_layers" else \
                           "0.7" if column_name == "local_model_temperature" else "NULL"
            
            try:
                # Add the column with direct SQL
                sql = f"ALTER TABLE settings ADD COLUMN {column_name} {column_type} DEFAULT {default_value}"
                print(f"Executing SQL: {sql}")
                session.execute(sa.text(sql))
                session.commit()
                print(f"Column {column_name} added successfully.")
            except Exception as e:
                session.rollback()
                print(f"Error adding column {column_name}: {str(e)}")
                traceback.print_exc()
                migration_success = False
        else:
            print(f"Column {column_name} already exists. Skipping.")
    
    if migration_success:
        print("Migration completed successfully.")
    else:
        print("Migration completed with errors. Some columns may not have been added.")
    
    # Close the session
    try:
        session.close()
        print("Database session closed.")
    except Exception as e:
        print(f"Error closing database session: {str(e)}")

if __name__ == "__main__":
    run_migration()