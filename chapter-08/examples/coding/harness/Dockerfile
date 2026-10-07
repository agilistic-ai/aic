FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends bash git tmux \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /harness/requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /harness/requirements.txt
COPY agent.py candidate_call.py /harness/
ENV PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
WORKDIR /work
ENTRYPOINT ["python", "-I", "-B", "/harness/agent.py"]
