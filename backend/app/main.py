"""Sahi Dawa backend entry point.

Currently exposes the deterministic catalogue/matching/pricing layer.
RAG explanation, patient history and pattern detection are separate
layers to be wired in on top of this by other services.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

app = FastAPI(title="Sahi Dawa API")

# Permissive CORS: the frontend is normally served from this same origin
# (see the StaticFiles mount below), but this also lets the API be called
# directly from a separately-hosted frontend or from /docs during testing.
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allowed_origins == "*" else allowed_origins.split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# Serve the thin-client frontend from the same service, at the same origin,
# so there is no CORS to configure for the default deployment. The frontend
# lives in ../../frontend-web relative to this file (backend/app/main.py).
_frontend_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend-web",
)
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
