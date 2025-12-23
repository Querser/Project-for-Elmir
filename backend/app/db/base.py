from __future__ import annotations

# В проекте уже есть Base в app.models.base
# Делаем единый источник истины, чтобы relationship/metadata работали нормально.
from app.models.base import Base

__all__ = ["Base"]
