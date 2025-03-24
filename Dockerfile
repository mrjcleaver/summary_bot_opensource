FROM python:3.11 AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Configure Poetry to install dependencies in the project directory
RUN poetry config virtualenvs.in-project true

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-interaction --no-ansi

# Slim runtime image
FROM python:3.11-slim

WORKDIR /app

# Copy the virtual environment and application code
COPY --from=builder /app/.venv .venv/
COPY . .

# Set the virtual environment path
ENV PATH="/app/.venv/bin:$PATH"

# Run the application
CMD ["python", "src/main.py"]