# ObserveCo — Runtime observability for AI agent systems
# Multi-stage build for minimal image size

# --- Build stage ---
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN pip install --no-cache-dir hatch

# Copy source
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

# Build wheel
RUN pip install --no-cache-dir --prefix=/install .

# --- Runtime stage ---
FROM python:3.12-slim AS runtime

# Security: non-root user
RUN groupadd -r observeco && useradd -r -g observeco -d /home/observeco -s /sbin/nologin observeco

# Install runtime dependencies only
RUN pip install --no-cache-dir \
    colorama>=0.4.6 \
    platformdirs>=3.0.0 \
    typer>=0.9 \
    rich>=13 \
    httpx>=0.27 \
    fastapi>=0.110 \
    "uvicorn[standard]>=0.27" \
    jinja2>=3.1 \
    python-multipart>=0.0.9

# Copy built package
COPY --from=builder /install /usr/local

# Create data directories
RUN mkdir -p /home/observeco/.local/share/observeco \
    && chown -R observeco:observeco /home/observeco

# Environment
ENV PYTHONUNBUFFERED=1
ENV OBSERVECO_DATA_DIR=/home/observeco/.local/share/observeco

USER observeco
WORKDIR /home/observeco

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')" || exit 1

# Default: run dashboard
CMD ["python", "-m", "observeco.cli", "dashboard", "--port", "8080"]
