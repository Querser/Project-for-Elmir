from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router as api_v1_router
from app.core.config import get_settings
from app.core.exceptions import setup_exception_handlers
from app.core.logger import configure_logging
from app.core.middleware import RequestLoggingMiddleware, TelegramAuthMiddleware

settings = get_settings()
configure_logging()

logger = logging.getLogger("app.main")

app = FastAPI(
    title="Volleyball MiniApp API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(TelegramAuthMiddleware)

setup_exception_handlers(app)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def healthcheck():
    return {"status": "ok"}
