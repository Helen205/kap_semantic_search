FROM python:3.9-slim

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


RUN echo '#!/bin/bash\n\
if [ "$1" = "api" ]; then\n\
    uvicorn api:app --host 0.0.0.0 --port 8001\n\
elif [ "$1" = "celery_worker" ]; then\n\
    celery -A excel_to_html worker --loglevel=info\n\
elif [ "$1" = "celery_beat" ]; then\n\
    celery -A excel_to_html beat --loglevel=info\n\
else\n\
    echo "Unknown command: $1"\n\
    exit 1\n\
fi' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["api"]
