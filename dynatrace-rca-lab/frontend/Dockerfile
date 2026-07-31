FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && opentelemetry-bootstrap -a install

COPY . .

# Auto-instrument Flask + requests; no-ops when OTEL_SDK_DISABLED=true
CMD ["opentelemetry-instrument", "python", "app.py"]
