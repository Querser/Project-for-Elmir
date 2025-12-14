# app/api/v1/__init__.py

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import system

api_router = APIRouter()

# Системные/тестовые ручки
api_router.include_router(system.router, tags=["system"])
