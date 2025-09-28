

from fastapi import FastAPI
from contextlib import asynccontextmanager

from starlette.middleware.cors import CORSMiddleware

from app.api.v1.routers import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在 worker 启动时执行（等同于以前的 startup）
    from app.core.logging_config import setup_logging
    from app.database.database import init_db
    setup_logging()
    await init_db()
    # 确保需要在启动时导入的模块被导入（比如注册任务）
    import app.flow.sync_new_movie_flow  # noqa: F401
    import tmdbsimple as tmdb
    from app.core.config import settings

    tmdb.API_KEY = settings.TMDB_API_KEY

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

    origins = ["http://localhost:3000","http://192.168.31.2:3000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,  # 允许的源
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
