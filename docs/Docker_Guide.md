# Docker Deployment Guide

This guide provides detailed instructions for deploying PrivacyChatBoX using Docker and Docker Compose, including troubleshooting tips and best practices.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- Docker Engine (version 20.10.0 or higher)
- Docker Compose (version 2.0.0 or higher)
- Git (optional, for cloning the repository)

## Basic Deployment

### Step 1: Get the Code

Either clone the repository or download and extract the source code:

```bash
git clone https://github.com/yourusername/PrivacyChatBoX.git
cd PrivacyChatBoX
```

### Step 2: Configure Environment Variables (Optional)

You can configure environment variables in two ways:

1. Create a `.env` file in the project root directory with your API keys and settings:

```
# AI Provider Keys
OPENAI_API_KEY=your_openai_key
CLAUDE_API_KEY=your_claude_key
GEMINI_API_KEY=your_gemini_key
SERPAPI_KEY=your_serpapi_key

# Azure AD Integration (if needed)
AZURE_TENANT_ID=your_azure_tenant_id
AZURE_CLIENT_ID=your_azure_client_id
AZURE_CLIENT_SECRET=your_azure_client_secret
AZURE_REDIRECT_URI=your_redirect_uri

# Microsoft DLP Integration (if needed)
MS_TENANT_ID=your_tenant_id
MS_CLIENT_ID=your_client_id
MS_CLIENT_SECRET=your_client_secret
MS_DLP_ENDPOINT_ID=your_endpoint_id
```

2. Or, edit the `docker-compose.yml` file directly to add your environment variables.

### Step 3: Start the Application

Run the following command to start the application in detached mode:

```bash
docker-compose up -d
```

This will:
- Build the Docker image (if not already built)
- Create and start the PostgreSQL database container
- Create and start the application container
- Create persistent volumes for the database and local LLM models

### Step 4: Access the Application

Open your web browser and navigate to:

```
http://localhost:5000
```

### Step 5: Stop the Application

To stop the application, run:

```bash
docker-compose down
```

To stop the application and remove all volumes (WARNING: this will delete all data, including the database):

```bash
docker-compose down -v
```

## Development Environment

For development purposes, an extended configuration is provided in `docker-compose.override.yml`:

```bash
# Start with development configuration
docker-compose -f docker-compose.yml -f docker-compose.override.yml up
```

This configuration includes:
- Mounting the current directory into the container for live code changes
- Adding Adminer for database management (accessible at http://localhost:8080)
- Setting a DEVELOPMENT environment variable

## Troubleshooting Docker Deployment

### Database Connection Issues

**Problem**: The application can't connect to the database.

**Solutions**:
1. Check if the database container is running:
   ```bash
   docker-compose ps
   ```

2. Check database logs:
   ```bash
   docker-compose logs db
   ```

3. Ensure the database environment variables in `docker-compose.yml` match the connection string:
   ```
   DATABASE_URL=postgresql://postgres:postgres@db:5432/privacychatbox
   ```

### Container Startup Issues

**Problem**: The application container exits immediately or fails to start.

**Solutions**:
1. Check application logs:
   ```bash
   docker-compose logs app
   ```

2. Run the container in interactive mode to debug:
   ```bash
   docker-compose run --rm app bash
   ```

3. Check if the entrypoint script is executable:
   ```bash
   docker-compose exec app ls -la /app/docker-entrypoint.sh
   ```

### Migration Failures

**Problem**: Database migrations are failing.

**Solutions**:
1. Check migration logs:
   ```bash
   docker-compose logs app
   ```

2. Run migrations manually:
   ```bash
   docker-compose exec app python database_check.py
   docker-compose exec app python migration_add_dlp_columns.py
   docker-compose exec app python migration_add_local_llm_columns.py
   docker-compose exec app python migration_pattern_levels.py
   ```

### Port Conflicts

**Problem**: The port 5000 is already in use on your system.

**Solution**: 
1. Modify the port mapping in `docker-compose.yml`:
   ```yaml
   ports:
     - "8888:5000"  # Change 5000 to an available port on your host
   ```

## Custom Docker Builds

### Using a Different PostgreSQL Version

To use a different PostgreSQL version, modify the `db` service in `docker-compose.yml`:

```yaml
db:
  image: postgres:14-alpine  # Change to your preferred version
```

### Optimizing the Application Image

To reduce the Docker image size:

1. Use multi-stage builds in your Dockerfile
2. Remove development dependencies
3. Use Alpine-based images where possible

## Production Deployment Tips

For production deployments, consider:

1. **Use Secrets Management**:
   - Don't store API keys in the Docker Compose file
   - Use Docker secrets or a secure environment variable management solution

2. **Configure HTTPS**:
   - Set up a reverse proxy (Nginx, Traefik) with SSL termination
   - Obtain and configure SSL certificates

3. **Database Backup Strategy**:
   - Set up regular PostgreSQL backups
   - Consider using a managed database service instead of a container

4. **Monitoring**:
   - Add health checks to the docker-compose.yml
   - Set up container monitoring and logging