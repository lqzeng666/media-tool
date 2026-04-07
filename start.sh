#!/bin/bash
# Start both backend and frontend

# Start FastAPI backend
uvicorn backend.server:app --host 0.0.0.0 --port 8100 &

# Start Streamlit frontend
streamlit run app/main.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false

