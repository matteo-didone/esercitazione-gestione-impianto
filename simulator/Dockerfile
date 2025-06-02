# Simulator Docker Image
FROM python:3.11-slim

LABEL maintainer="IoT Industrial Team"
LABEL description="Industrial Plant Simulator"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create logs directory
RUN mkdir -p logs

# Copy simulator code
COPY simulator.py .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash simulator && \
    chown -R simulator:simulator /app

# Switch to non-root user
USER simulator

# Environment variables with defaults
ENV MQTT_BROKER=mosquitto
ENV MQTT_PORT=1883
ENV TIME_MULTIPLIER=10
ENV PIECE_COUNT=10
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "simulator.py"]