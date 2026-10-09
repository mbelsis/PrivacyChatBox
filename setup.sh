#!/bin/bash
set -e

# PrivacyChatBoX Setup Script
# This script sets up the PrivacyChatBoX application with all required dependencies,
# database configuration, and initial setup.

# Color codes for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print a section header
section() {
    echo -e "\n${BLUE}===== $1 =====${NC}\n"
}

# Print a success message
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Print a warning message
warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Print an error message
error() {
    echo -e "${RED}✗ $1${NC}"
}

# Print an info message
info() {
    echo -e "🔹 $1"
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

set_env_var() {
    local key="$1"
    local value="$2"
    python - "$key" "$value" <<'PY'
from pathlib import Path
import sys

key = sys.argv[1]
value = sys.argv[2]
path = Path(".env")
lines = []
if path.exists():
    lines = path.read_text(encoding="utf-8").splitlines()

updated = False
for index, line in enumerate(lines):
    if line.startswith(f"{key}="):
        lines[index] = f"{key}={value}"
        updated = True
        break

if not updated:
    lines.append(f"{key}={value}")

path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

# Main setup function
main() {
    section "PrivacyChatBoX Setup Script"
    
    info "This script will set up PrivacyChatBoX with the following steps:"
    info "1. Check system requirements"
    info "2. Create a Python virtual environment"
    info "3. Install required Python packages"
    info "4. Set up the PostgreSQL database"
    info "5. Create required directories"
    info "6. Run database migrations"
    info "7. Set up environment variables"
    
    echo ""
    read -p "Press Enter to continue or Ctrl+C to abort..."
    
    # Check system requirements
    check_system_requirements
    
    # Create Python virtual environment
    create_virtual_environment
    
    # Install required packages
    install_requirements
    
    # Set up PostgreSQL database
    setup_database
    
    # Create required directories
    create_directories
    
    # Set up environment variables
    setup_env_variables
    
    # Run database migrations
    run_migrations
    
    # Setup complete
    section "Setup Complete"
    success "PrivacyChatBoX has been successfully set up!"
    
    echo ""
    info "To start the application:"
    echo "  source venv/bin/activate"
    echo "  streamlit run app.py"
    echo ""
    
    info "Bootstrap admin account:"
    echo "  Username: admin"
    echo "  Password: printed in the application log on first start"
    echo "            (or DEFAULT_ADMIN_PASSWORD from .env if you set a strong one)"
    
    warning "You will be asked to change the bootstrap password at first login."
    echo ""
    
    section "Docker Deployment Alternative"
    info "PrivacyChatBoX can also be deployed using Docker:"
    echo ""
    echo "  1. Make sure Docker and Docker Compose are installed"
    echo "  2. Run: docker-compose up -d"
    echo "  3. Access the application at http://localhost:5000"
    echo ""
    info "For development with Docker:"
    echo "  docker-compose -f docker-compose.yml -f docker-compose.override.yml up"
    echo ""
    info "For more details, see the Docker Guide:"
    echo "  docs/Docker_Guide.md"
    echo ""
}

# Check system requirements
check_system_requirements() {
    section "Checking System Requirements"
    
    # Check Python version
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d '.' -f 1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d '.' -f 2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
            success "Python $PYTHON_VERSION found"
        else
            error "Python 3.10+ is required, but found $PYTHON_VERSION"
            exit 1
        fi
    else
        error "Python 3 not found. Please install Python 3.10 or higher."
        exit 1
    fi
    
    # Check pip
    if command_exists pip3; then
        success "pip3 found"
    else
        error "pip3 not found. Please install pip for Python 3."
        exit 1
    fi
    
    # Check PostgreSQL
    if command_exists psql; then
        PSQL_VERSION=$(psql --version | cut -d ' ' -f 3)
        success "PostgreSQL $PSQL_VERSION found"
    else
        warning "PostgreSQL not found. You will need to install PostgreSQL or provide remote PostgreSQL credentials."
        read -p "Do you want to continue without PostgreSQL? (y/n): " answer
        if [ "$answer" != "y" ]; then
            exit 1
        fi
    fi
    
    # Check virtualenv
    if command_exists virtualenv; then
        success "virtualenv found"
    else
        info "Installing virtualenv..."
        pip3 install virtualenv
        if [ $? -eq 0 ]; then
            success "virtualenv installed"
        else
            error "Failed to install virtualenv. Please install it manually."
            exit 1
        fi
    fi
}

# Create Python virtual environment
create_virtual_environment() {
    section "Creating Python Virtual Environment"
    
    if [ -d "venv" ]; then
        warning "Virtual environment already exists in 'venv' directory."
        read -p "Do you want to recreate it? (y/n): " answer
        if [ "$answer" == "y" ]; then
            info "Removing existing virtual environment..."
            rm -rf venv
        else
            success "Using existing virtual environment"
            return
        fi
    fi
    
    info "Creating virtual environment in 'venv' directory..."
    virtualenv venv -p python3
    
    if [ $? -eq 0 ]; then
        success "Virtual environment created"
    else
        error "Failed to create virtual environment"
        exit 1
    fi
    
    info "Activating virtual environment..."
    source venv/bin/activate
    
    if [ $? -eq 0 ]; then
        success "Virtual environment activated"
    else
        error "Failed to activate virtual environment"
        exit 1
    fi
}

# Install required packages
install_requirements() {
    section "Installing Required Packages"
    
    info "Installing required Python packages from pyproject.toml..."
    pip install .
    
    if [ $? -eq 0 ]; then
        success "Required packages installed"
    else
        error "Failed to install required packages"
        exit 1
    fi
}

# Set up PostgreSQL database
setup_database() {
    section "Setting Up PostgreSQL Database"
    
    if ! command_exists psql; then
        warning "PostgreSQL not found. Skipping database setup."
        warning "You'll need to configure the DATABASE_URL manually in the .env file."
        return
    fi
    
    read -p "Would you like to create a new PostgreSQL database for PrivacyChatBoX? (y/n): " create_db
    
    if [ "$create_db" == "y" ]; then
        read -p "Database name (default: privacychatbox): " db_name
        db_name=${db_name:-privacychatbox}
        
        read -p "Database user (default: postgres): " db_user
        db_user=${db_user:-postgres}
        
        read -rsp "Database password: " db_password
        echo ""
        
        read -p "Database host (default: localhost): " db_host
        db_host=${db_host:-localhost}
        
        read -p "Database port (default: 5432): " db_port
        db_port=${db_port:-5432}
        
        info "Creating database $db_name..."
        
        # Check if the database already exists
        if PGPASSWORD="$db_password" psql -h "$db_host" -p "$db_port" -U "$db_user" -lqt | cut -d \| -f 1 | grep -qw "$db_name"; then
            warning "Database $db_name already exists."
            read -p "Do you want to drop and recreate it? (y/n): " drop_db
            
            if [ "$drop_db" == "y" ]; then
                PGPASSWORD="$db_password" psql -h "$db_host" -p "$db_port" -U "$db_user" -c "DROP DATABASE $db_name;"
                success "Database $db_name dropped"
            else
                success "Using existing database $db_name"
                export DATABASE_URL="postgresql://$db_user:$db_password@$db_host:$db_port/$db_name"
                return
            fi
        fi
        
        # Create the database
        PGPASSWORD="$db_password" psql -h "$db_host" -p "$db_port" -U "$db_user" -c "CREATE DATABASE $db_name;"
        
        if [ $? -eq 0 ]; then
            success "Database $db_name created"
            
            # Set the DATABASE_URL environment variable
            export DATABASE_URL="postgresql://$db_user:$db_password@$db_host:$db_port/$db_name"
            
            # Add DATABASE_URL to .env file
            set_env_var "DATABASE_URL" "postgresql://$db_user:$db_password@$db_host:$db_port/$db_name"
            
            success "Database URL set in .env file"
        else
            error "Failed to create database $db_name"
            exit 1
        fi
    else
        warning "Skipping database creation. You'll need to configure the DATABASE_URL manually in the .env file."
    fi
}

# Create required directories
create_directories() {
    section "Creating Required Directories"
    
    # Create .streamlit directory if it doesn't exist
    if [ ! -d ".streamlit" ]; then
        mkdir -p .streamlit
        success "Created .streamlit directory"
        
        # Create config.toml with server settings
        echo "[server]" > .streamlit/config.toml
        echo "headless = true" >> .streamlit/config.toml
        echo "address = \"0.0.0.0\"" >> .streamlit/config.toml
        echo "port = 5000" >> .streamlit/config.toml
        
        success "Created .streamlit/config.toml with server settings"
    else
        success ".streamlit directory already exists"
    fi
    
    # Create models directory for local LLMs
    if [ ! -d "models" ]; then
        mkdir -p models
        success "Created models directory for local LLMs"
    else
        success "models directory already exists"
    fi
    
    # Create assets directory if it doesn't exist
    if [ ! -d "assets" ]; then
        mkdir -p assets
        success "Created assets directory"
    else
        success "assets directory already exists"
    fi
}

# Set up environment variables
setup_env_variables() {
    section "Setting Up Environment Variables"
    
    # Check if .env file exists
    if [ -f ".env" ]; then
        info ".env file exists. Adding missing variables..."
    else
        info "Creating .env file..."
        touch .env
    fi
    
    # Add optional environment variables with prompts
    read -p "Would you like to configure API keys for AI providers now? (y/n): " configure_api
    
    if [ "$configure_api" == "y" ]; then
        echo "" >> .env
        echo "# AI Provider API Keys" >> .env
        
        read -rsp "OpenAI API Key (press Enter to skip): " openai_key
        echo ""
        if [ -n "$openai_key" ]; then
            set_env_var "OPENAI_API_KEY" "$openai_key"
            success "Added OpenAI API Key"
        fi
        
        read -rsp "Anthropic Claude API Key (press Enter to skip): " claude_key
        echo ""
        if [ -n "$claude_key" ]; then
            set_env_var "ANTHROPIC_API_KEY" "$claude_key"
            success "Added Anthropic Claude API Key"
        fi
        
        read -rsp "Google Gemini API Key (press Enter to skip): " gemini_key
        echo ""
        if [ -n "$gemini_key" ]; then
            set_env_var "GOOGLE_API_KEY" "$gemini_key"
            success "Added Google Gemini API Key"
        fi
        
        read -rsp "SerpAPI Key for web search (press Enter to skip): " serpapi_key
        echo ""
        if [ -n "$serpapi_key" ]; then
            set_env_var "SERPAPI_KEY" "$serpapi_key"
            success "Added SerpAPI Key"
        fi
    else
        info "Skipping API key configuration. You can add these later in the .env file or through the Settings page."
    fi
    
    read -p "Would you like to configure Azure AD integration? (y/n): " configure_azure
    
    if [ "$configure_azure" == "y" ]; then
        echo "" >> .env
        echo "# Azure AD Authentication" >> .env
        
        read -p "Azure Client ID: " azure_client_id
        set_env_var "AZURE_CLIENT_ID" "$azure_client_id"

        read -rsp "Azure Client Secret: " azure_client_secret
        echo ""
        set_env_var "AZURE_CLIENT_SECRET" "$azure_client_secret"
        
        read -p "Azure Tenant ID: " azure_tenant_id
        set_env_var "AZURE_TENANT_ID" "$azure_tenant_id"
        
        read -p "Azure Redirect URI (default: http://localhost:5000/): " azure_redirect_uri
        azure_redirect_uri=${azure_redirect_uri:-http://localhost:5000/}
        set_env_var "AZURE_REDIRECT_URI" "$azure_redirect_uri"
        
        success "Added Azure AD configuration"
    fi
    
    read -p "Would you like to configure Microsoft DLP integration? (y/n): " configure_dlp
    
    if [ "$configure_dlp" == "y" ]; then
        echo "" >> .env
        echo "# Microsoft DLP Integration" >> .env
        
        read -p "Microsoft Client ID: " ms_client_id
        set_env_var "MS_CLIENT_ID" "$ms_client_id"

        read -rsp "Microsoft Client Secret: " ms_client_secret
        echo ""
        set_env_var "MS_CLIENT_SECRET" "$ms_client_secret"
        
        read -p "Microsoft Tenant ID: " ms_tenant_id
        set_env_var "MS_TENANT_ID" "$ms_tenant_id"
        
        success "Added Microsoft Purview configuration"
        info "Grant the app InformationProtectionPolicy.Read.All, Content.Process.User and ContentActivity.Write (application) with admin consent."
    fi

    # Encryption at rest: generate a key once and never overwrite an existing one.
    existing_key=$(python -c "from dotenv import dotenv_values; print(dotenv_values('.env').get('DATA_ENCRYPTION_KEY') or '')")
    if [ -z "$existing_key" ]; then
        new_key=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
        set_env_var "DATA_ENCRYPTION_KEY" "$new_key"
        success "Generated DATA_ENCRYPTION_KEY for encryption at rest"
        warning "Back up DATA_ENCRYPTION_KEY securely: encrypted data cannot be recovered without it."
    else
        success "DATA_ENCRYPTION_KEY already configured"
    fi
    
    success "Environment variables configured"
}

# Run database migrations
run_migrations() {
    section "Running Database Migrations"
    
    if [ -z "$DATABASE_URL" ]; then
        if [ -f ".env" ]; then
            DATABASE_URL=$(python -c "from dotenv import dotenv_values; print(dotenv_values('.env').get('DATABASE_URL',''))")
            export DATABASE_URL
        fi
    fi
    
    if [ -z "$DATABASE_URL" ]; then
        error "DATABASE_URL is not set. Cannot run migrations."
        warning "You will need to run migrations manually after setting up the DATABASE_URL."
        return
    fi
    
    info "Running database schema check and migrations..."
    python database_check.py
    
    if [ $? -eq 0 ]; then
        success "Database migrations completed successfully"
    else
        warning "Some database migrations may have failed. Check the output above for details."
        warning "You may need to run migrations manually:"
        echo "  python migration_add_dlp_columns.py"
        echo "  python migration_add_local_llm_columns.py"
    fi
}

# Run the main function
main
