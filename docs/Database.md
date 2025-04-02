# PrivacyChatBoX Database Documentation

This document provides detailed information about the database structure of PrivacyChatBoX, including table schemas and relationships.

## Database Overview

PrivacyChatBoX uses a PostgreSQL database to store user information, settings, conversations, and privacy detection events. The application uses SQLAlchemy as an ORM (Object-Relational Mapper) to interact with the database.

## Database Configuration

The application connects to the database using a connection string stored in the `DATABASE_URL` environment variable. This URL should be in the format:

```
postgresql://username:password@hostname:port/database_name
```

Example configuration in `.env` file:
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/privacychatbox
```

## Database Connection

The database connection is managed in the `database.py` file, which provides functions to initialize the database and manage sessions:

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Base class for all models
Base = declarative_base()

# Database URL from environment variable
DATABASE_URL = os.environ.get("DATABASE_URL")

# Database engine
engine = None

# Session factory
SessionLocal = None

def init_db():
    """Initialize the database connection"""
    global engine, SessionLocal
    
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create all tables if they don't exist
    Base.metadata.create_all(bind=engine)

def get_session():
    """Get a new database session"""
    if SessionLocal is None:
        init_db()
    return SessionLocal()

def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = get_session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
```

## Database Schema

### Users Table

Stores user authentication and profile information.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    password VARCHAR NOT NULL,
    role VARCHAR DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW(),
    azure_id VARCHAR UNIQUE,
    azure_name VARCHAR
);

COMMENT ON COLUMN users.role IS 'admin or user';
```

### Settings Table

Stores user-specific settings for AI providers, privacy scanning, and Microsoft DLP integration.

```sql
CREATE TABLE settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    llm_provider VARCHAR DEFAULT 'openai',
    ai_character VARCHAR DEFAULT 'assistant',
    openai_api_key VARCHAR DEFAULT '',
    openai_model VARCHAR DEFAULT 'gpt-4o',
    claude_api_key VARCHAR DEFAULT '',
    claude_model VARCHAR DEFAULT 'claude-3-5-sonnet-20241022',
    gemini_api_key VARCHAR DEFAULT '',
    gemini_model VARCHAR DEFAULT 'gemini-1.5-pro',
    serpapi_key VARCHAR DEFAULT '',
    local_model_path VARCHAR DEFAULT '',
    scan_enabled BOOLEAN DEFAULT TRUE,
    scan_level VARCHAR DEFAULT 'standard',
    auto_anonymize BOOLEAN DEFAULT TRUE,
    disable_scan_for_local_model BOOLEAN DEFAULT TRUE,
    custom_patterns JSON DEFAULT '[]',
    enable_ms_dlp BOOLEAN DEFAULT TRUE,
    ms_dlp_sensitivity_threshold VARCHAR DEFAULT 'confidential',
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON COLUMN settings.llm_provider IS 'openai, claude, gemini, local';
COMMENT ON COLUMN settings.scan_level IS 'standard, strict';
COMMENT ON COLUMN settings.ms_dlp_sensitivity_threshold IS 'general, internal, confidential, highly_confidential, secret, top_secret';
```

### Conversations Table

Stores metadata about user conversations.

```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR DEFAULT 'New Conversation',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Messages Table

Stores individual messages within conversations.

```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

COMMENT ON COLUMN messages.role IS 'user or assistant';
```

### Files Table

Stores metadata about files attached to messages.

```sql
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
    original_name VARCHAR NOT NULL,
    path VARCHAR NOT NULL,
    mime_type VARCHAR NOT NULL,
    size INTEGER NOT NULL,
    scan_result JSON
);
```

### Detection Events Table

Stores privacy detection events for analytics and auditing.

```sql
CREATE TABLE detection_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT NOW(),
    action VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    detected_patterns JSON NOT NULL,
    file_names VARCHAR DEFAULT ''
);

COMMENT ON COLUMN detection_events.action IS 'scan, anonymize';
COMMENT ON COLUMN detection_events.severity IS 'low, medium, high';
```

## Entity Relationship Diagram

```
User (1) ---> (0..1) Settings
  |
  |------> (0..N) Conversations
  |           |
  |           +-----> (0..N) Messages
  |                      |
  |                      +-----> (0..N) Files
  |
  +------> (0..N) DetectionEvents
```

## Database Migrations

The application includes migration scripts to update the database schema as needed. For example, `migration_add_dlp_columns.py` adds Microsoft DLP integration columns to the Settings table:

```python
def run_migration():
    """
    Add Microsoft DLP integration columns to the Settings table
    """
    # Initialize database connection
    engine = create_engine(os.environ.get("DATABASE_URL"))
    
    # Check if columns already exist
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("settings")]
    
    # Add columns if they don't exist
    if "enable_ms_dlp" not in columns:
        with engine.connect() as connection:
            connection.execute(text("""
                ALTER TABLE settings 
                ADD COLUMN enable_ms_dlp BOOLEAN DEFAULT TRUE,
                ADD COLUMN ms_dlp_sensitivity_threshold VARCHAR DEFAULT 'confidential'
            """))
            print("Added Microsoft DLP integration columns to Settings table")
    else:
        print("Microsoft DLP integration columns already exist")
```

## Setting Up a New Database

To set up a new PostgreSQL database for PrivacyChatBoX:

1. Install PostgreSQL if not already installed.

2. Create a new database:
   ```sql
   CREATE DATABASE privacychatbox;
   ```

3. Create a user (optional, you can use an existing user):
   ```sql
   CREATE USER privacychatbox_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE privacychatbox TO privacychatbox_user;
   ```

4. Set the `DATABASE_URL` environment variable in your `.env` file:
   ```
   DATABASE_URL=postgresql://privacychatbox_user:your_password@localhost:5432/privacychatbox
   ```

5. Run the application with `streamlit run app.py` - the database tables will be created automatically using SQLAlchemy's `create_all()` method.

6. Run any migration scripts if needed:
   ```bash
   python migration_add_dlp_columns.py
   ```

## Working with the Database

The application uses SQLAlchemy's ORM to interact with the database. Here's an example of how to query and modify data:

```python
from database import get_session
from models import User, Settings

# Create a new user
def create_user(username, password, role="user"):
    session = get_session()
    try:
        # Check if user already exists
        existing_user = session.query(User).filter(User.username == username).first()
        if existing_user:
            return None
        
        # Create new user
        new_user = User(username=username, password=hash_password(password), role=role)
        session.add(new_user)
        session.commit()
        
        # Create default settings for the user
        default_settings = Settings(user_id=new_user.id)
        session.add(default_settings)
        session.commit()
        
        return new_user.id
    finally:
        session.close()
```

## Database Backup and Restoration

To backup the PostgreSQL database:

```bash
pg_dump -U username -d privacychatbox > privacychatbox_backup.sql
```

To restore from a backup:

```bash
psql -U username -d privacychatbox < privacychatbox_backup.sql
```