"""
Migration script to add Microsoft DLP integration columns to the Settings table
"""
import os
import psycopg2
from sqlalchemy import create_engine, Column, Boolean, String, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")

def run_migration():
    """
    Add Microsoft DLP integration columns to the Settings table
    """
    print("Starting migration to add Microsoft DLP columns to Settings table...")
    
    # Connect to the database
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    
    try:
        # Check if the columns already exist
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'enable_ms_dlp'"))
        if result.fetchone():
            print("Column 'enable_ms_dlp' already exists in the Settings table")
        else:
            # Add enable_ms_dlp column
            conn.execute(text("ALTER TABLE settings ADD COLUMN enable_ms_dlp BOOLEAN DEFAULT TRUE"))
            print("Added 'enable_ms_dlp' column to Settings table")
        
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'ms_dlp_sensitivity_threshold'"))
        if result.fetchone():
            print("Column 'ms_dlp_sensitivity_threshold' already exists in the Settings table")
        else:
            # Add ms_dlp_sensitivity_threshold column
            conn.execute(text("ALTER TABLE settings ADD COLUMN ms_dlp_sensitivity_threshold VARCHAR DEFAULT 'confidential'"))
            print("Added 'ms_dlp_sensitivity_threshold' column to Settings table")
        
        print("Migration completed successfully")
    except Exception as e:
        print(f"Error during migration: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()