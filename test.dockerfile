FROM python:3.12-slim AS requirements-stage

ENV PYTHONUNBUFFERED 1

WORKDIR /api_backend

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libffi-dev libssl-dev && \
    pip install --upgrade pip && \
    pip install --no-cache-dir --upgrade poetry && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY poetry.lock pyproject.toml ./
COPY . .

RUN poetry install

EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]