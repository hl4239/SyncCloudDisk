# -*- coding: utf-8 -*-
"""
应用主入口文件 (Application Entrypoint)

该文件负责创建和配置FastAPI应用实例，并将所有API路由挂载到主应用上。
使用 uvicorn 启动此文件即可运行整个Web服务。
"""
import contextlib
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.containers import container, init_singleton
from app.interfaces.tasks_api import router

logger = logging.getLogger()


# 2. 定义生命周期事件管理器
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 应用启动时执行的代码 ---
    print("应用启动中...")
    # 在这里执行你的异步初始化
    await init_singleton(container)

    yield  # 这是分隔点，应用会在这里运行

    # # --- 应用关闭时执行的代码 ---
    # print("应用关闭中...")
    # # 在这里可以添加清理代码，比如关闭 aiohttp session
    # await container.douban_crawler().close()  # 假设你给爬虫添加了 close 方法
    # await container.them_movie_crawler().close()  # 假设你给爬虫添加了 close 方法
# --- 创建 FastAPI 应用实例 ---
app = FastAPI(
    title="分层架构的异步任务处理API",
    description="一个遵循整洁架构(Clean Architecture)思想构建的FastAPI应用，支持后台任务处理。",
    version="2.0.0",
    # 可选：为Swagger UI文档添加更多信息
    contact={
        "name": "Your Name",
        "url": "http://your-website.com",
        "email": "your-email@example.com",
    },lifespan=lifespan
    # 可选：设置根路径，用于反向代理后修正文档路径
    # openapi_prefix="/api/v1"
)

# --- 配置中间件 (Middleware) ---
# 配置CORS (跨源资源共享) 中间件，允许所有来源的请求，这在开发中很方便。
# 在生产环境中，应该将其限制为你的前端应用的域名。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有HTTP头
)

# --- 挂载 API 路由 (Include Routers) ---
# 这是将你的API端点连接到主应用的关键步骤。
# 我们将 tasks.py 中定义的 router 对象包含进来。
# FastAPI 会自动处理其 `prefix` 和 `tags` 设置。
app.include_router(router)

# --- 定义根路由 (Optional) ---
# 定义一个简单的根路径，可以用于健康检查或提供API文档链接。
@app.get("/", tags=["Root"])
def read_root():
    """
    API的根路径，提供欢迎信息和文档链接。
    """
    return {
        "message": "欢迎使用异步任务处理API",
        "documentation": "/docs"  # FastAPI 自动生成的 Swagger UI 文档
    }


# --- 启动说明 ---
# 要启动此应用，请在终端中运行以下命令 (确保你在项目的根目录下):
#
# uvicorn main:app --reload
#
# - `uvicorn`: ASGI服务器。
# - `main`: 指的是 `main.py` 文件。
# - `app`: 指的是在 `main.py` 中创建的 FastAPI 实例 `app = FastAPI()`。
# - `--reload`: 启用热重载，当代码文件发生变化时，服务器会自动重启。这在开发时非常有用。
#
# 服务启动后，你可以在浏览器中访问 http://127.0.0.1:8000/docs 查看交互式API文档。

# 你也可以在代码中直接启动，但这通常只用于调试，不推荐用于生产。
