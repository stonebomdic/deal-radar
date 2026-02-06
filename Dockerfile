# =============================================================================
# Stage 1: Builder - install Python dependencies and Playwright
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build-essential for any compiled Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy project metadata and install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir . && \
    pip install --no-cache-dir playwright && \
    playwright install chromium

# =============================================================================
# Stage 2: Runtime - minimal image with only what's needed
# =============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install system dependencies required by Playwright Chromium
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libnss3 \
        libnspr4 \
        libdbus-1-3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libatspi2.0-0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libpango-1.0-0 \
        libcairo2 \
        libasound2 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy Playwright browsers from builder
COPY --from=builder /root/.cache/ms-playwright /home/appuser/.cache/ms-playwright

# Copy application source code
COPY pyproject.toml ./
COPY src/ ./src/

# Install the project (non-editable)
RUN pip install --no-cache-dir --no-deps .

# Create directories for data and logs
RUN mkdir -p /app/data /app/logs

# Set ownership of app directory to appuser
RUN chown -R appuser:appuser /app /home/appuser/.cache

USER appuser

# Expose the API port
EXPOSE 8000

# Health check against the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: start the API server
CMD ["python", "-m", "src.cli", "serve"]
