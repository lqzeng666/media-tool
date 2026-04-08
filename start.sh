#!/bin/bash
# Render sets $PORT (default 10000) - Streamlit MUST listen on it
# Backend runs internally on 8100

export BACKEND_URL="http://localhost:8100"

# Start FastAPI backend (internal only, localhost)
uvicorn backend.server:app --host 127.0.0.1 --port 8100 &

sleep 3

# Streamlit listens on Render's $PORT
exec streamlit run app/main.py \
  --server.port "${PORT:-8501}" \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false \
  --browser.gatherUsageStats false
