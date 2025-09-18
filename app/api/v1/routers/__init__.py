# app/api/v1/routers/__init__.py
from fastapi import APIRouter

from .tasks import router as tasks_router

router = APIRouter()
# 你之前定义的 /health, /hello 等
@router.get("/health")
def health_check():
    return {"status": "ok"}

# 把 tasks 子路由挂载到 /api/v1/tasks
router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
