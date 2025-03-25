FROM python:3.11 AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install Poetry
RUN pip install "poetry>=1.2.0"

# Configure Poetry to install dependencies in the project directory
RUN poetry config virtualenvs.in-project true

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Accept a build-time argument to include dev dependencies
ARG INSTALL_DEV=false

# Install dependencies conditionally using pyproject.toml's dev-dependencies
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        poetry install --no-interaction --no-ansi --no-root --with dev; \
    else \
        poetry install --no-interaction --no-ansi --no-root; \
    fi

# Slim runtime image
FROM python:3.11-slim

WORKDIR /app

# Copy the virtual environment and application code
COPY --from=builder /app/.venv .venv/
COPY . .

# Set the virtual environment path
ENV PATH="/app/.venv/bin:$PATH"

# Run the application using the virtual environment (python is using venv's poetry)
# TODO  make frozen_modules dependent on the environment INSTALL_DEV using an external script 
CMD ["python", "-Xfrozen_modules=off", "src/main.py"]
