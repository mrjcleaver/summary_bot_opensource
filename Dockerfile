FROM python:3.11 AS builder


# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
ARG INSTALL_DEV=false

# Install Poetry
RUN pip install "poetry>=1.2.0"

# Configure Poetry to install dependencies in the project directory
RUN poetry config virtualenvs.in-project true


# Copy dependency files
COPY pyproject.toml poetry.lock ./



# Install dependencies conditionally using pyproject.toml's dev-dependencies
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        poetry install --no-interaction --no-ansi --no-root --with dev; \
    else \
        poetry install --no-interaction --no-ansi --no-root; \
    fi

#### FINAL IMAGE ####
# Slim runtime image
FROM python:3.11-slim

# Accept a  argument to include dev dependencies during runtime
ARG INSTALL_DEV=false


WORKDIR /app

RUN if [ "$INSTALL_DEV" = "true" ]; then \
        apt-get update && apt-get install -y 6tunnel; \
    fi

RUN which 6tunnel

# Copy the virtual environment and application code
COPY --from=builder /app/.venv .venv/
COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# This is not a healthcheck because its only used in development.
LABEL debugpy.healthcheck="connections.py verifies IDE debugger tunnel + session"

# Copy the script into the image
COPY bin/connections.py /app/bin/connections.py

# Make it executable (optional)
RUN chmod +x /app/bin/connections.py


# Set the virtual environment path
ENV PATH="/app/.venv/bin:$PATH"


CMD ["/entrypoint.sh"]
