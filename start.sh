#!/bin/bash
# Start both backend and frontend
# Render provides $PORT env var for the externally-exposed port

STREAMLIT_PORT=${PORT:-8501}

# Start FastAPI backend (internal only)
uvicorn backend.server:app --host 0.0.0.0 --port 8100 &

# Wait for backend to start
sleep 2

# Start Streamlit frontend on Render's exposed port
streamlit run app/main.py \
  --server.port "$STREAMLIT_PORT" \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false \
  --browser.gatherUsageStats false
