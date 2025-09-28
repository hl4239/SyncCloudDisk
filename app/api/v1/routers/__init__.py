# app/api/v1/routers/__init__.py
from fastapi import APIRouter

from app.database.models import SystemConfig, Movie
from app.utils.generic_crud import GenericCRUDRouter
from .tasks import router as tasks_router
from .workflows import router as workflows_router
from .scheduler import router as scheduler_router
from .panclouds import router as pancloud_router
from  .movies import  router as movies_router
router = APIRouter()
# 你之前定义的 /health, /hello 等
@router.get("/health")
def health_check():
    return {"status": "ok"}

# 把 tasks 子路由挂载到 /api/v1/tasks
router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
router .include_router(workflows_router,prefix="/workflows", tags=["workflows"])
router.include_router(scheduler_router, prefix="/scheduler", tags=["scheduler"])
router.include_router(pancloud_router, prefix="/panclouds", tags=["panclouds"])
# router.include_router(movies_router, prefix="/movies", tags=["movies"])
router.include_router(GenericCRUDRouter(Movie).router)
router.include_router(GenericCRUDRouter(SystemConfig).router)
