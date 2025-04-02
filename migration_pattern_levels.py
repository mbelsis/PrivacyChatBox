"""
Migration script to add 'level' attribute to custom patterns in Settings table
"""
import json
from sqlalchemy import create_engine, text
from database import get_session, session_scope
from models import Settings

def run_migration():
    """
    Add 'level' attribute to custom patterns in Settings table
    """
    try:
        print("Running migration: Adding level attribute to custom patterns...")
        
        # Get all users with settings
        with session_scope() as session:
            settings_list = session.query(Settings).all()
            
            # Process each user's settings
            for settings in settings_list:
                # Get custom patterns
                custom_patterns = settings.get_custom_patterns()
                modified = False
                
                if custom_patterns:
                    # Check if any pattern is missing the level attribute
                    for i, pattern in enumerate(custom_patterns):
                        if isinstance(pattern, dict) and "name" in pattern and "pattern" in pattern:
                            if "level" not in pattern:
                                # Add level attribute (default to standard)
                                pattern["level"] = "standard"
                                modified = True
                    
                    # Update patterns if modified
                    if modified:
                        settings.custom_patterns = custom_patterns
                        print(f"Updated patterns for user ID {settings.user_id}")
            
            # Commit changes
            print("Migration completed successfully!")
            
    except Exception as e:
        print(f"Error running migration: {str(e)}")
        return False
        
    return True

if __name__ == "__main__":
    run_migration()