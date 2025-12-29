from fastapi import APIRouter

from app.api.v1 import (
    admin_billing,
    admin_notifications,
    enrollments,
    levels,
    notifications,
    profile,
    ratings,
    system,
    trainings,
)

api_router = APIRouter()

api_router.include_router(system.router)
api_router.include_router(profile.router)
api_router.include_router(trainings.router)
api_router.include_router(enrollments.router)
api_router.include_router(levels.router)
api_router.include_router(ratings.router)

# admin
api_router.include_router(admin_billing.router)
api_router.include_router(admin_notifications.router)

# stage9
api_router.include_router(notifications.router)
