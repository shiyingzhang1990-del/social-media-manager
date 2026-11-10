#!/bin/bash
# Social Media Manager - Start script
# This starts the backend server on http://127.0.0.1:8765

cd "$(dirname "$0")"
echo "======================================"
echo "  Social Media Manager v1.0.0"
echo "  Starting server..."
echo "======================================"

# Check if Python3 is available
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found"
  exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
  source venv/bin/activate
  pip install -r backend/requirements.txt -q
else
  source venv/bin/activate
fi

echo ""
echo "  Dashboard: http://127.0.0.1:8765"
echo "  API:       http://127.0.0.1:8765/api/health"
echo "  Press Ctrl+C to stop"
echo "======================================"

python3 -m backend.main
