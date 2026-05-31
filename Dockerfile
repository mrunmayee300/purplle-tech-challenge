FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV DATASET_ROOT=/data
ENV VIDEO_DIR=/data/videos
ENV LAYOUT_PATH=/data/store_layout.json
ENV POS_PATH=/data/pos_transactions.csv

RUN mkdir -p /app/data

EXPOSE 8000 8501

COPY docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh 2>/dev/null || sed -i '' 's/\r$//' /entrypoint.sh 2>/dev/null || true
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
