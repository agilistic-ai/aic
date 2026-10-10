# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends bash git tmux \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /harness/requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /harness/requirements.txt
COPY agent.py candidate_call.py LICENSE.txt DISCLAIMER.md /harness/
ENV PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
WORKDIR /work
ENTRYPOINT ["python", "-I", "-B", "/harness/agent.py"]
