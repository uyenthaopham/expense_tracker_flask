# ============================================================================
# Dockerfile – Expense Tracker Flask
# Multi-stage build: builder → runtime
# ============================================================================

# ------------------------------------
# Stage 1 – Builder (install deps)
# ------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install OS-level build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual environment
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ------------------------------------
# Stage 2 – Runtime (lean image)
# ------------------------------------
FROM python:3.11-slim AS runtime

LABEL maintainer="expense-tracker" \
      description="Expense Tracker Flask – production image"

# Non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Runtime OS deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy application code
COPY . .

# Correct ownership
RUN chown -R appuser:appuser /app

USER appuser

# Expose Gunicorn port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run with Gunicorn (production WSGI server)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--threads", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "run:app"]
