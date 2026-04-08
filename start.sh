#!/bin/bash
# Start both backend and frontend
# Backend is internal only (127.0.0.1), Streamlit is exposed

export BACKEND_URL="http://localhost:8100"

# Start FastAPI backend (internal only)
uvicorn backend.server:app --host 127.0.0.1 --port 8100 &

sleep 3

# Start Streamlit on the port Render expects
# Render reads EXPOSE from Dockerfile, so we use 8501
exec streamlit run app/main.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false \
  --browser.gatherUsageStats false
