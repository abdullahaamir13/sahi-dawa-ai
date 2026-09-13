# Sahi Dawa — single-service image.
# FastAPI serves the JSON API AND the static frontend from the same origin,
# so there's nothing to CORS-configure in the default deployment.

FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY data data
COPY frontend-web frontend-web

WORKDIR /app/backend

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
