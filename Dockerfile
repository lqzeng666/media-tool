FROM python:3.11-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser
RUN playwright install --with-deps chromium

# Copy application code
COPY . .

# Render exposes $PORT (default 10000), Streamlit listens on it
# Backend runs internally on 8100
EXPOSE 10000

# Start script
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]
