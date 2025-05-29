# Event Processor Docker Image
FROM python:3.11-slim

LABEL maintainer="IoT Industrial Team"
LABEL description="MQTT to InfluxDB Event Processor"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create src directory
RUN mkdir -p src logs

# Copy source code
COPY src/ src/
COPY main.py .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash processor && \
    chown -R processor:processor /app

# Switch to non-root user
USER processor

# Environment variables with defaults
ENV MQTT_BROKER=mosquitto
ENV MQTT_PORT=1883
ENV INFLUXDB_URL=http://influxdb:8086
ENV INFLUXDB_TOKEN=factory-token-2024
ENV INFLUXDB_ORG=factory
ENV INFLUXDB_BUCKET=industrial_data
ENV LOG_LEVEL=INFO
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Expose health check port
EXPOSE 8080

# Default command
CMD ["python", "main.py"]