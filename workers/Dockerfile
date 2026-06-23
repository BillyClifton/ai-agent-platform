FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Install gateway deps first (worker imports gateway models)
COPY ../gateway/requirements.txt ./gateway-requirements.txt
RUN pip install --no-cache-dir -r gateway-requirements.txt

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY ../gateway /app/gateway/
COPY . /app/workers/

CMD ["python", "-m", "workers.main"]
