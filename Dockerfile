FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY . .

# HF Spaces uses port 7860
ENV PORT=7860
ENV BACKEND_URL=http://localhost:8100
EXPOSE 7860

COPY start.sh .
RUN chmod +x start.sh
CMD ["./start.sh"]
