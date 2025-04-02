# Docker Setup Guide for PrivacyChatBoX

This guide provides detailed instructions for setting up and using PrivacyChatBoX with Docker, making deployment easy and consistent across environments.

## Prerequisites

Before starting, ensure you have:

- **Docker** installed (version 20.10.0 or higher)
- **Docker Compose** installed (version 2.0.0 or higher)
- Git (optional, for cloning the repository)

## Quick Start Guide

### Step 1: Get the Application Code

Clone the repository or download the source code:

```bash
git clone https://github.com/yourusername/PrivacyChatBoX.git
cd PrivacyChatBoX
```

### Step 2: Configure Environment Variables (Optional)

You have two options to configure environment variables:

#### Option A: Create a .env file

Create a `.env` file in the project root directory with your API keys:

```
# Database Configuration (already set in docker-compose.yml)
# DATABASE_URL=postgresql://postgres:postgres@db:5432/privacychatbox

# AI Provider API Keys
OPENAI_API_KEY=your_openai_api_key
CLAUDE_API_KEY=your_claude_api_key
GEMINI_API_KEY=your_gemini_api_key
SERPAPI_KEY=your_serpapi_key

# Azure AD Integration (if needed)
AZURE_TENANT_ID=your_azure_tenant_id
AZURE_CLIENT_ID=your_azure_client_id
AZURE_CLIENT_SECRET=your_azure_client_secret
AZURE_REDIRECT_URI=http://localhost:5000/

# Microsoft DLP Integration (if needed)
MS_TENANT_ID=your_tenant_id
MS_CLIENT_ID=your_client_id
MS_CLIENT_SECRET=your_client_secret
MS_DLP_ENDPOINT_ID=your_endpoint_id
```

#### Option B: Edit docker-compose.yml

Alternatively, you can directly edit the `docker-compose.yml` file and uncomment the environment variables section.

### Step 3: Start the Application

For production use:

```bash
docker-compose up -d
```

This command:
- Builds the application container if it doesn't exist
- Creates and starts the PostgreSQL database container
- Creates and starts the application container
- Sets up persistent volumes for data and models
- Runs in detached mode (-d)

### Step 4: Access the Application

Open your web browser and navigate to:

```
http://localhost:5000
```

Use the default login credentials:
- Username: **admin**
- Password: **admin**

**Important:** Change the admin password after your first login through the Admin panel.

## Development Environment

For development purposes, use:

```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml up
```

This gives you:
- Live code reloading (your local files are mounted into the container)
- Adminer database management tool at http://localhost:8080
- Containers running in foreground with visible logs

### Accessing the Database with Adminer

1. Open http://localhost:8080 in your browser
2. Log in with:
   - System: PostgreSQL
   - Server: db
   - Username: postgres
   - Password: postgres
   - Database: privacychatbox

## Managing Docker Containers

### View Running Containers

```bash
docker-compose ps
```

### Stop the Application

```bash
docker-compose down
```

To also remove volumes (WARNING: this deletes all data):

```bash
docker-compose down -v
```

### View Logs

```bash
# All logs
docker-compose logs

# Application logs only
docker-compose logs app

# Database logs only
docker-compose logs db

# Follow logs in real-time
docker-compose logs -f
```

### Rebuild Containers

If you've made changes to the Dockerfile:

```bash
docker-compose build
docker-compose up -d
```

## Configuration Details

### Container Structure

PrivacyChatBoX uses two main containers:

1. **app**: The main application container
   - Based on Python 3.11
   - Runs Streamlit on port 5000
   - Contains all application code
   - Handles database migrations on startup

2. **db**: PostgreSQL database
   - Uses PostgreSQL 15 Alpine image
   - Stores all application data
   - Accessible to the app container

### Volume Configuration

Two persistent volumes are configured:

1. **postgres_data**: Stores the database data
   - Location: /var/lib/postgresql/data in the db container
   - Persists between container restarts

2. **models_data**: Stores downloaded local LLM models
   - Location: /app/models in the app container
   - Persists between container restarts

### Network Configuration

Both containers run on the same Docker network, allowing:
- The app container to access the db container via hostname "db"
- Port 5000 to be exposed to the host machine
- Port 8080 (Adminer) to be exposed in development mode

## Troubleshooting

### Application Doesn't Start

Check the logs:

```bash
docker-compose logs app
```

Common issues:
- Database connection problems
- Missing environment variables
- Permission issues with mounted volumes

### Database Connection Issues

Verify database container is running:

```bash
docker-compose ps db
```

Check database logs:

```bash
docker-compose logs db
```

Ensure environment variables match in docker-compose.yml:
```
DATABASE_URL=postgresql://postgres:postgres@db:5432/privacychatbox
```

### Container Access Issues

You can access a shell in the running container:

```bash
docker-compose exec app bash
```

From here, you can:
- Run Python scripts directly
- Check file permissions
- Verify environment variables
- Run database migrations manually

### Database Migration Issues

If migrations fail, you can run them manually:

```bash
docker-compose exec app python database_check.py
docker-compose exec app python migration_add_dlp_columns.py
docker-compose exec app python migration_add_local_llm_columns.py
docker-compose exec app python migration_pattern_levels.py
```

## Production Deployment Tips

### Security Considerations

For production deployment:

1. **Don't expose Adminer**: Remove docker-compose.override.yml in production
2. **Use Secrets Management**: 
   - Consider using Docker Secrets or environment variables instead of hardcoding in docker-compose.yml
   - Never commit .env files with sensitive information to version control
3. **Set Strong Passwords**:
   - Change default PostgreSQL password
   - Change admin user password immediately

### Performance Optimization

1. **Allocate Sufficient Resources**:
   - CPU/Memory limits can be set in docker-compose.yml
   - Consider your workload when sizing containers

2. **Database Tuning**:
   - PostgreSQL can be tuned for performance by setting environment variables in docker-compose.yml

### Backup Strategy

For regular database backups:

```bash
# Backup
docker-compose exec db pg_dump -U postgres privacychatbox > backup_$(date +%Y%m%d).sql

# Restore
cat backup_file.sql | docker-compose exec -T db psql -U postgres privacychatbox
```

## Advanced Configuration

### Using a Different Port

To use a different port (e.g., 8888 instead of 5000), edit docker-compose.yml:

```yaml
ports:
  - "8888:5000"  # Maps host port 8888 to container port 5000
```

### Using External PostgreSQL

To use an external PostgreSQL server instead of the container:

1. Edit docker-compose.yml to remove the db service
2. Update the DATABASE_URL environment variable to point to your external PostgreSQL server
3. Remove the depends_on section for the db service

### Adding SSL/TLS

For production deployments, consider adding a reverse proxy (like Nginx or Traefik) with SSL termination.