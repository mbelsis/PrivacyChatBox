FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the dependency manifest first to leverage Docker layer caching
COPY pyproject.toml /app/

# Install the dependencies declared in pyproject.toml (single source of truth)
RUN pip install --no-cache-dir -U pip && \
    python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))" > /tmp/requirements.txt && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/models /app/.streamlit

# Create Streamlit config
RUN echo "[server]" > /app/.streamlit/config.toml && \
    echo "headless = true" >> /app/.streamlit/config.toml && \
    echo "address = \"0.0.0.0\"" >> /app/.streamlit/config.toml && \
    echo "port = 5000" >> /app/.streamlit/config.toml

# Make entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Expose port for the application
EXPOSE 5000

# Use our entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]
