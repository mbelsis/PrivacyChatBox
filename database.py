import os
import time
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import streamlit as st
from contextlib import contextmanager

# Load database connection details from environment variables
DB_HOST = os.environ.get("PGHOST", "localhost")
DB_PORT = os.environ.get("PGPORT", "5432")
DB_NAME = os.environ.get("PGDATABASE", "privacychatbox")
DB_USER = os.environ.get("PGUSER", "postgres")
DB_PASSWORD = os.environ.get("PGPASSWORD", "postgres")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Create SQLAlchemy base class
Base = declarative_base()

# Engine and session factory
engine = None
SessionLocal = None

# Connection retry settings
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

def init_db():
    """Initialize the database connection"""
    global engine, SessionLocal
    
    retry_count = 0
    last_error = None
    
    while retry_count < MAX_RETRIES:
        try:
            # Try to use DATABASE_URL if available
            if DATABASE_URL:
                engine = create_engine(
                    DATABASE_URL,
                    pool_pre_ping=True,  # Enable connection health checks
                    pool_recycle=3600    # Recycle connections after 1 hour
                )
            else:
                # Otherwise construct the connection string from individual components
                conn_str = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
                engine = create_engine(
                    conn_str,
                    pool_pre_ping=True,
                    pool_recycle=3600
                )
            
            # Create session factory
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            
            # Test the connection first
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text("SELECT 1"))
            
            # Create tables if they don't exist
            # We'll import the models here to avoid circular imports
            from models import User, Settings, DetectionEvent, Conversation, Message, File
            
            # Check if tables exist before creating them
            inspector = sqlalchemy.inspect(engine)
            existing_tables = inspector.get_table_names()
            
            if 'users' not in existing_tables:
                # If tables don't exist, create them
                Base.metadata.create_all(engine)
            
            return True
        except Exception as e:
            last_error = e
            retry_count += 1
            
            if retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                st.error(f"Database connection error after {MAX_RETRIES} attempts: {str(e)}")
                return False
    
    return False

def get_session():
    """Get a new database session"""
    if SessionLocal is None:
        init_db()
    
    if SessionLocal is None:
        st.error("Failed to initialize database connection")
        return None
    
    session = SessionLocal()
    try:
        # Test the session with a simple query
        session.execute(sqlalchemy.text("SELECT 1"))
        return session
    except:
        session.close()
        raise

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    if SessionLocal is None:
        init_db()
        
    if SessionLocal is None:
        st.error("Failed to initialize database connection")
        yield None
        return
        
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
