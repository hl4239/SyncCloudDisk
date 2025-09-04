from typing import Optional, Callable, Coroutine, Any
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
import asyncio

from app.database.models import PanCloud, SplitTitleSeasonRegular, OpenAISource

# 使用 motor + beanie 异步初始化数据库
_client: Optional[AsyncIOMotorClient] = None

async def init_db():
	"""初始化 MongoDB（motor 客户端）并使用 Beanie 注册文档模型。
	返回 motor 的 Database 对象。
	"""
	global _client
	if _client is None:
		_client = AsyncIOMotorClient(settings.MONGODB_URI)
		db = _client.get_default_database()
		# 注册 Beanie 文档模型（会自动创建索引）
		# beanie 需要数据库实例和 Document 列表进行初始化；为了避免循环依赖，这里延迟导入 models
		from app.database.models import Movie

		await init_beanie(database=db, document_models=[Movie,PanCloud,SplitTitleSeasonRegular,OpenAISource],)
	else:
		db = _client.get_default_database()
	return db

def get_client() -> Optional[AsyncIOMotorClient]:
	return _client

def get_database():
	if _client:
		return _client.get_default_database()
	return None

# 事务助手：在 MongoDB 中使用会话执行事务（需要 MongoDB 副本集或单节点启用事务）
async def run_transaction(func: Callable[..., Coroutine[Any, Any, Any]], *args, **kwargs):
    """在事务会话中运行异步函数，函数第一个参数将会得到 session 对象。

    func: async 函数，签名应为 async def func(session, *args, **kwargs)
    """
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    async with await client.start_session() as session:
        async with session.start_transaction():
            return await func(session, *args, **kwargs)


# 简单同步封装用于测试（在同步上下文中启动事件循环并初始化）
def init_db_sync():
    return asyncio.get_event_loop().run_until_complete(init_db())
