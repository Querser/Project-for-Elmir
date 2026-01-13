from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.location import Location
from app.models.training import Training
from app.models.user import User
from app.models.notification import Notification


def seed_locations(db: Session) -> list[Location]:
    existing = db.query(Location).count()
    if existing > 0:
        return db.query(Location).all()

    loc1 = Location(
        name="Пляжка Школьная",
        address="Москва, Школьная, 1/1",
        metro="Площадь Ильича",
        latitude=55.747,
        longitude=37.681,
        maps_url="https://yandex.ru/maps/?text=Москва%2C%20Школьная%2C%201%2F1",
        video_url="https://www.youtube.com/",
    )
    loc2 = Location(
        name="Пляжка Хорошевка",
        address="Москва, Хорошёвское шоссе, 27",
        metro="Полежаевская",
        latitude=55.777,
        longitude=37.521,
        maps_url="https://yandex.ru/maps/?text=Москва%2C%20Хорошёвское%20шоссе%2C%2027",
        video_url="https://www.youtube.com/",
    )

    db.add_all([loc1, loc2])
    db.commit()
    return [loc1, loc2]


def seed_trainings(db: Session, locations: list[Location]) -> None:
    if db.query(Training).count() > 0:
        return

    now = datetime.now(timezone.utc)

    t1 = Training(
        title="Пляжка, групповая тренировка",
        description="Тренировка с тренером",
        start_at=now + timedelta(days=1, hours=2),
        duration_minutes=120,
        price=550,
        capacity_main=10,
        capacity_reserve=4,
        coach_name="Роман Иванов",
        location_id=locations[0].id,
        min_level_name="Лайт",
        max_level_name="Медиум",
        image_url="https://images.pexels.com/photos/945471/pexels-photo-945471.jpeg?auto=compress&cs=tinysrgb&w=800",
        video_url=locations[0].video_url,
    )

    t2 = Training(
        title="Игровая ночь 3×3",
        description="Игровая ночь на песке",
        start_at=now + timedelta(days=2, hours=6),
        duration_minutes=150,
        price=750,
        capacity_main=16,
        capacity_reserve=6,
        coach_name="Линар Мустаев",
        location_id=locations[1].id,
        min_level_name="Лайт+",
        max_level_name="Лайт Pro",
        image_url="https://images.pexels.com/photos/4761792/pexels-photo-4761792.jpeg?auto=compress&cs=tinysrgb&w=800",
        video_url=locations[1].video_url,
    )

    db.add_all([t1, t2])
    db.commit()


def seed_user_and_notifications(db: Session) -> None:
    """
    Создадим тестового пользователя и пару уведомлений.
    Для Telegram авторизации у пользователя должен быть telegram_id.
    """
    user = db.query(User).filter(User.telegram_id == 123456789).first()
    if not user:
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            is_active=True,
            rating=120,
            cups=3,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # если уведомления уже есть — не плодим
    if db.query(Notification).filter(Notification.user_id == user.id).count() > 0:
        return

    n1 = Notification(
        user_id=user.id,
        type="INFO",
        title="Добро пожаловать!",
        body="Это тестовое уведомление. Оно должно быть видно в приложении.",
        text="Это тестовое уведомление. Оно должно быть видно в приложении.",
        is_read=False,
    )
    n2 = Notification(
        user_id=user.id,
        type="TRAINING",
        title="Тренировка завтра",
        body="Не забудь: завтра тренировка! Проверь расписание.",
        text="Не забудь: завтра тренировка! Проверь расписание.",
        is_read=False,
    )
    db.add_all([n1, n2])
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        locations = seed_locations(db)
        seed_trainings(db, locations)
        seed_user_and_notifications(db)
        print("✅ seed_demo_data: данные успешно добавлены в БД")


if __name__ == "__main__":
    main()
