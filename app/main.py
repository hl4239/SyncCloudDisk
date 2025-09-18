

from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.v1.routers import router as v1_router
from app.core.logging_config import setup_logging
from app.database.database import init_db
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在 worker 启动时执行（等同于以前的 startup）
    setup_logging()
    await init_db()
    # 确保需要在启动时导入的模块被导入（比如注册任务）
    import app.flow.tasks  # noqa: F401
    try:
        yield
    finally:
        # 在这里做清理工作（等同于以前的 shutdown）
        # e.g. await task_manager.cancel_all() 或关闭 DB 连接
        pass

def create_app() -> FastAPI:
    app = FastAPI(
        title="SyncCloudDisk API",
        version="1.0.0",
        description="A FastAPI backend service",
        lifespan=lifespan
    )
    app.include_router(v1_router, prefix="/api/v1")
    # 显式注册默认应用，指向 app/pages
    # 挂载 Solara 应用到 /solara 路径

    return app


app = create_app()
if __name__ == "__main__":
    import uvicorn
    # 推荐将 log_config 交由 setup_logging 管理；如果需要可传 None
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
