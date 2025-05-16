FROM python:3.12.6-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .


RUN mkdir -p /app/logs /app/last_processed

RUN pip install --no-cache-dir fastapi uvicorn

CMD ["python", "src/main.py"]

