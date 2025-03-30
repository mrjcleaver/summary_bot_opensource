#### Dockerfile for Python application with Poetry and optional dev dependencies
# This Dockerfile builds a Python application using Poetry for dependency management.
# It allows for the installation of development dependencies and includes a script to set up a tunnel for IPv6 IDE debugging.

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
        rm -rf /var/lib/apt/lists/* && \
        which 6tunnel; \
    fi

# Copy the virtual environment and application code
COPY --from=builder /app/.venv .venv/
COPY . .


COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN if [ "$INSTALL_DEV" = "true" ]; then \
        /app/bin/tunnel-pydev-for-ipv6.sh && echo "tunnel-pydev-for-ipv6.sh executed"; \
    fi

COPY bin/debugpy-connections-test.py /app/bin/debugpy-connections-test.py
RUN chmod +x /app/bin/debugpy-connections-test.py


# Set the virtual environment path
ENV PATH="/app/.venv/bin:$PATH"


CMD ["/entrypoint.sh"]
