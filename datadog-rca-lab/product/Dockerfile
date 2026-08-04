FROM python:3.12-slim
WORKDIR /app
COPY product/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY product/app.py .
ENV DD_LOGS_INJECTION=true \
    DD_PROFILING_ENABLED=false \
    DD_RUNTIME_METRICS_ENABLED=true \
    PYTHONUNBUFFERED=1
EXPOSE 8081
CMD ["ddtrace-run", "python", "app.py"]
