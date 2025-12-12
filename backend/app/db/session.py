from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Временно используем localhost для БД.
# Позже переключим на docker-контейнер (db) через переменные окружения.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/volleyball_db"
)

# Создаем синхронный engine (psycopg2)
engine = create_engine(DATABASE_URL, echo=False, future=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Зависимость FastAPI для получения сессии БД.
    Каждый запрос будет получать свою сессию и корректно её закрывать.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
