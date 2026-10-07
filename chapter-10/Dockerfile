FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
COPY src ./src
COPY config.toml .
ENV PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
CMD ["python", "-m", "uvicorn", "ai_cookbook.desk_api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-access-log"]
