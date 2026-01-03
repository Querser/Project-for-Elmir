from __future__ import annotations

# Единый источник истины для Base.
# ВАЖНО: никаких импортов моделей здесь быть не должно — иначе ловишь циклы.
from app.models.base import Base

__all__ = ["Base"]
