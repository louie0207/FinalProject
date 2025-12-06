# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies into a temporary location
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install .

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app ./app
COPY helper_lib ./helper_lib
COPY frontend.py .

# Create necessary data directories so permission errors don't occur
RUN mkdir -p data/raw_filings data/chunks data/indexes

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Make sure to pass OPENAI_API_KEY at runtime!

# Expose ports for both services
EXPOSE 8000
EXPOSE 8501

# Default command runs the Backend API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]