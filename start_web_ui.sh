#!/bin/bash
# Quick start script for Web UI

cd "$(dirname "$0")"

# Set environment variables
# STYLE is empty by default - users can set via UI if needed
export STYLE=""

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Install web UI dependencies if needed
if ! python -c "import flask" 2>/dev/null; then
    echo "Installing Flask dependencies..."
    pip install -r web_ui/requirements.txt
fi

# Run Flask app
echo "Starting Web UI on http://localhost:5000"
python -m flask --app web_ui.app run --host=0.0.0.0 --port=5000

