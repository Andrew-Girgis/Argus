FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

RUN uv pip install --system --no-cache \
    "mlflow==3.14.0" \
    "boto3>=1.35.0" \
    "psycopg2-binary>=2.9.10"

EXPOSE 5000

ENTRYPOINT ["mlflow"]
