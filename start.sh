#!/bin/bash
# Start both backend and frontend on Render
# Render sets $PORT for the externally-exposed port (default 10000)

export STREAMLIT_PORT=${PORT:-8501}
export BACKEND_PORT=8100

# Ensure backend URL points to internal port
export BACKEND_URL="http://localhost:${BACKEND_PORT}"

# Start FastAPI backend (internal, not exposed)
uvicorn backend.server:app --host 127.0.0.1 --port "$BACKEND_PORT" &

# Wait for backend to be ready
sleep 3

# Start Streamlit on Render's exposed port
exec streamlit run app/main.py \
  --server.port "$STREAMLIT_PORT" \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false \
  --browser.gatherUsageStats false
