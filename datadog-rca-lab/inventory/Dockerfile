FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY common /app/common
COPY inventory/app.py /app/app.py
ENV DD_LOGS_INJECTION=true \
    DD_PROFILING_ENABLED=false \
    DD_RUNTIME_METRICS_ENABLED=true \
    PYTHONUNBUFFERED=1 \
    LOG_DIR=/logs \
    PYTHONPATH=/app
EXPOSE 8082
CMD ["ddtrace-run", "python", "app.py"]
