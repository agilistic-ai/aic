# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
COPY src ./src
COPY config.toml LICENSE.txt DISCLAIMER.md .
ENV PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
CMD ["python", "-m", "uvicorn", "ai_cookbook.desk_api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-access-log"]
