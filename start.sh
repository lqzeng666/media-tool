#!/bin/bash
export BACKEND_URL="http://localhost:8100"
export PYTHONPATH="/app"

# Start FastAPI backend internally
uvicorn backend.server:app --host 127.0.0.1 --port 8100 &
sleep 3

# Run streamlit_app.py from project root - this ensures /app is in sys.path
exec streamlit run streamlit_app.py \
  --server.port "${PORT:-7860}" \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false \
  --browser.gatherUsageStats false
