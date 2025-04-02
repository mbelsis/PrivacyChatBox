#!/usr/bin/env python3
"""
Database Schema Validation Script

This script checks the database schema to ensure all required columns are present
and runs any missing migrations if needed.
"""

import os
import sys
import logging
from sqlalchemy import inspect
from database import init_db, get_session
from models import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("database_check")

# List of required columns for the Settings table
DLP_COLUMNS = [
    "enable_ms_dlp",
    "ms_dlp_sensitivity_threshold"
]

LOCAL_LLM_COLUMNS = [
    "local_model_path",
    "local_model_context_size",
    "local_model_gpu_layers",
    "local_model_temperature"
]

def check_columns_exist(table_name, column_list):
    """
    Check if all columns in the list exist in the specified table
    
    Args:
        table_name: Name of the table to check
        column_list: List of column names to check for
        
    Returns:
        Tuple of (all_exist, missing_columns)
    """
    session = get_session()
    inspector = inspect(session.bind)
    
    try:
        existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
        missing_columns = [col for col in column_list if col not in existing_columns]
        
        all_exist = len(missing_columns) == 0
        return all_exist, missing_columns
    finally:
        session.close()

def run_migration(migration_module_name):
    """
    Import and run a migration module
    
    Args:
        migration_module_name: Name of the migration module
        
    Returns:
        True if migration succeeded, False otherwise
    """
    try:
        migration_module = __import__(migration_module_name)
        migration_module.run_migration()
        logger.info(f"Successfully ran migration: {migration_module_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to run migration {migration_module_name}: {e}")
        return False

def main():
    """Main function to check database schema and run migrations if needed"""
    logger.info("Initializing database connection...")
    init_db()
    
    # Check DLP columns
    logger.info("Checking Microsoft DLP columns...")
    dlp_columns_exist, missing_dlp_columns = check_columns_exist("settings", DLP_COLUMNS)
    
    if not dlp_columns_exist:
        logger.warning(f"Missing DLP columns: {missing_dlp_columns}")
        logger.info("Running DLP migration...")
        if run_migration("migration_add_dlp_columns"):
            logger.info("DLP migration successful")
        else:
            logger.error("DLP migration failed")
    else:
        logger.info("DLP columns exist")
    
    # Check Local LLM columns
    logger.info("Checking Local LLM columns...")
    llm_columns_exist, missing_llm_columns = check_columns_exist("settings", LOCAL_LLM_COLUMNS)
    
    if not llm_columns_exist:
        logger.warning(f"Missing Local LLM columns: {missing_llm_columns}")
        logger.info("Running Local LLM migration...")
        if run_migration("migration_add_local_llm_columns"):
            logger.info("Local LLM migration successful")
        else:
            logger.error("Local LLM migration failed")
    else:
        logger.info("Local LLM columns exist")
    
    # Run pattern levels migration to ensure all custom patterns have level attribute
    logger.info("Running pattern levels migration...")
    if run_migration("migration_pattern_levels"):
        logger.info("Pattern levels migration successful")
    else:
        logger.error("Pattern levels migration failed")
    
    # Final check after migrations
    dlp_columns_exist, missing_dlp_columns = check_columns_exist("settings", DLP_COLUMNS)
    llm_columns_exist, missing_llm_columns = check_columns_exist("settings", LOCAL_LLM_COLUMNS)
    
    all_ok = dlp_columns_exist and llm_columns_exist
    
    if all_ok:
        logger.info("All database columns are properly configured")
        return 0
    else:
        logger.error("Some columns are still missing in the database schema")
        if not dlp_columns_exist:
            logger.error(f"Missing DLP columns: {missing_dlp_columns}")
        if not llm_columns_exist:
            logger.error(f"Missing Local LLM columns: {missing_llm_columns}")
        return 1

if __name__ == "__main__":
    sys.exit(main())