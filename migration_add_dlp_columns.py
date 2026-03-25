"""
Migration script to add Microsoft DLP integration columns to the Settings table
"""
from database import init_db, get_session
from sqlalchemy import text

def run_migration():
    """
    Add Microsoft DLP integration columns to the Settings table
    """
    print("Starting migration to add Microsoft DLP columns to Settings table...")

    if not init_db():
        print("Unable to initialize database connection for migration.")
        return

    session = get_session()
    if not session:
        print("Unable to create database session for migration.")
        return

    try:
        # Check if the columns already exist
        result = session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'enable_ms_dlp'"))
        if result.fetchone():
            print("Column 'enable_ms_dlp' already exists in the Settings table")
        else:
            # Add enable_ms_dlp column
            session.execute(text("ALTER TABLE settings ADD COLUMN enable_ms_dlp BOOLEAN DEFAULT TRUE"))
            print("Added 'enable_ms_dlp' column to Settings table")

        result = session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'ms_dlp_sensitivity_threshold'"))
        if result.fetchone():
            print("Column 'ms_dlp_sensitivity_threshold' already exists in the Settings table")
        else:
            # Add ms_dlp_sensitivity_threshold column
            session.execute(text("ALTER TABLE settings ADD COLUMN ms_dlp_sensitivity_threshold VARCHAR DEFAULT 'confidential'"))
            print("Added 'ms_dlp_sensitivity_threshold' column to Settings table")

        session.commit()
        print("Migration completed successfully")
    except Exception as e:
        session.rollback()
        print(f"Error during migration: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    run_migration()
