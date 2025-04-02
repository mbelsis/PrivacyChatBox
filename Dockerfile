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

# Copy requirements first to leverage Docker cache
COPY pyproject.toml /app/

# Install Python dependencies
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir streamlit anthropic azure-storage-blob google-generativeai \
    google-search-results jose llama-cpp-python msal msgraph-core openai pandas \
    plotly psycopg2-binary pyjwt python-dotenv python-jose reportlab requests \
    sqlalchemy tqdm

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