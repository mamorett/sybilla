#!/bin/bash
set -e

# Start server.py in the background
python server.py &

# Start FastAPI app for production (will keep the container running)
uvicorn app.main:app --host 0.0.0.0 --port 9090