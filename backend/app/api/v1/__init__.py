from fastapi import APIRouter

from app.api.v1 import (
    admin_audit_logs,
    admin_billing,
    admin_notifications,
    admin_settings,
    enrollments,
    levels,
    notifications,
    profile,
    ratings,
    system,
    trainings,
)
from app.api.v1.location import router as locations_router

api_router = APIRouter()

# public/user
api_router.include_router(system.router)
api_router.include_router(profile.router)
api_router.include_router(trainings.router)
api_router.include_router(enrollments.router)
api_router.include_router(levels.router)
api_router.include_router(ratings.router)
api_router.include_router(locations_router)

# stage9
api_router.include_router(notifications.router)

# admin
api_router.include_router(admin_billing.router)
api_router.include_router(admin_notifications.router)
api_router.include_router(admin_settings.router)
api_router.include_router(admin_audit_logs.router)
