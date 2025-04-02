# PrivacyChatBoX Package Requirements

This document lists all the Python packages required to run the PrivacyChatBoX application. These packages can be installed using pip:

```bash
pip install -r requirements.txt
```

## Core Dependencies

```
# Core dependencies
streamlit>=1.30.0
python-dotenv>=1.0.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.5
pandas>=2.0.0
requests>=2.28.0
plotly>=5.15.0
```

## AI Provider Dependencies

```
# AI Provider dependencies
openai>=1.10.0
anthropic>=0.8.0
google-generativeai>=0.3.0
```

## Authentication Dependencies

```
# Authentication dependencies
python-jose>=3.3.0
PyJWT>=2.6.0
msal>=1.22.0
msgraph-core>=0.2.2
```

## Web Search

```
# Web Search
google-search-results>=2.4.2
```

## PDF Export

```
# PDF Export
reportlab>=4.0.0
```

## Cloud Storage (for file handling)

```
# Cloud Storage
azure-storage-blob>=12.15.0
```

## Sensitive File Detection

```
# For sensitive file detection
python-magic>=0.4.27
```

## Development Tools (Optional)

```
# For development (optional)
pytest>=7.3.1
black>=23.3.0
flake8>=6.0.0
mypy>=1.3.0
```

## Installing Packages

In Replit, packages are already installed as specified in the `pyproject.toml` file:

```toml
[tool.poetry]
name = "PrivacyChatBoX"
version = "1.0.0"
description = "A privacy-focused AI chat platform with multiple model integrations"
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
streamlit = "^1.30.0"
python-dotenv = "^1.0.0"
sqlalchemy = "^2.0.0"
psycopg2-binary = "^2.9.5"
pandas = "^2.0.0"
requests = "^2.28.0"
openai = "^1.10.0"
anthropic = "^0.8.0"
google-generativeai = "^0.3.0"
python-jose = "^3.3.0"
PyJWT = "^2.6.0"
msal = "^1.22.0"
msgraph-core = "^0.2.2"
google-search-results = "^2.4.2"
reportlab = "^4.0.0"
azure-storage-blob = "^12.15.0"
plotly = "^5.15.0"

[tool.poetry.dev-dependencies]
pytest = "^7.3.1"
black = "^23.3.0"
flake8 = "^6.0.0"
mypy = "^1.3.0"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

For local development outside of Replit, you can install the packages using pip:

```bash
pip install -r requirements.txt
```

Or using Poetry:

```bash
poetry install
```