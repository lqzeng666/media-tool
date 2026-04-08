#!/bin/bash
export BACKEND_URL="http://localhost:8100"
export PYTHONPATH="/app:${PYTHONPATH}"

# Start FastAPI backend internally
uvicorn backend.server:app --host 127.0.0.1 --port 8100 &
sleep 3

# Start Streamlit
exec streamlit run app/main.py \
  --server.port "${PORT:-7860}" \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false \
  --browser.gatherUsageStats false
