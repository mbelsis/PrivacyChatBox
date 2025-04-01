import os
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import streamlit as st

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

def init_db():
    """Initialize the database connection"""
    global engine, SessionLocal
    
    try:
        # Try to use DATABASE_URL if available
        if DATABASE_URL:
            engine = create_engine(DATABASE_URL)
        else:
            # Otherwise construct the connection string from individual components
            conn_str = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
            engine = create_engine(conn_str)
        
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
        st.error(f"Database connection error: {str(e)}")
        return False

def get_session():
    """Get a new database session"""
    if SessionLocal is None:
        init_db()
    
    session = SessionLocal()
    try:
        return session
    except:
        session.close()
        raise
