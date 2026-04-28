from fastapi import APIRouter

from app.api.routes import assignments, backups, dashboard, employees, metrics, pilots, trino_runs

api_router = APIRouter()
api_router.include_router(pilots.router, tags=['pilots'])
api_router.include_router(employees.router, tags=['employees'])
api_router.include_router(assignments.router, tags=['assignments'])
api_router.include_router(metrics.router, tags=['metrics'])
api_router.include_router(dashboard.router, tags=['dashboard'])
api_router.include_router(trino_runs.router, tags=['trino-runs'])
api_router.include_router(backups.router, tags=['backup'])
