FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies (includes everything: ADK + Web UI)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create output directory
RUN mkdir -p output/posts logs

# Expose port
EXPOSE 7821

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV STYLE=""
ENV PORT=7821

# Run web UI with increased timeout for long-running generations
CMD ["gunicorn", "-b", "0.0.0.0:7821", "-w", "1", "--timeout", "600", "web_ui.app:app"]

