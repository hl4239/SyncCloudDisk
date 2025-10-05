import asyncio
import logging
import os
from typing import Optional, Dict

from telethon import TelegramClient

# 推荐改为从环境变量读取，避免把秘钥写入代码
# os.environ['TG_API_ID'] = '611335'
# os.environ['TG_API_HASH'] = 'your_api_hash_here'
logger=logging.getLogger(__name__)
API_ID = int(os.getenv('TG_API_ID', '611335'))   # or replace with your int directly
API_HASH = os.getenv('TG_API_HASH', 'd524b414d21f4d37f08684c1df41ac9c')  # replace or use env

class TGClient:
    def __init__(self, channel_name: str, session_name: Optional[str] = None):
        self.channel_name = channel_name
        # session_name 可选：为不同 channel 使用不同 session 文件，或统一使用 'user_session'
        self.session_name = session_name or f'user_session_{channel_name.strip("@")}'
        self.client = TelegramClient(self.session_name, API_ID, API_HASH)

    async def start(self):
        # start() 会处理登录流程（包括需要时显示二维码 / 请求手机号）
        await self.client.start()

    async def search_messages(self, search: str = '你好', limit: int = 5):
        # 迭代输出匹配到的消息
        async for message in self.client.iter_messages(self.channel_name, search=search, limit=limit):
            print(f"ID: {message.id}, 文本: {message.text}")

    async def send_messages_with_delete_old(
        self,
        pic: str,
        message: str,
        is_delete_old: bool = False,
        old_message_id: Optional[int] = None
    ):
        """
        如果 is_delete_old 且提供 old_message_id，则先删除该消息（在同一个对话中）。
        然后发送图片和 caption（message）。
        """
        if is_delete_old and old_message_id is not None:
            try:
                # delete_messages 可以接受单个 id 或列表
                await self.client.delete_messages(self.channel_name, old_message_id)
                logger.info(f"Deleted old message id={old_message_id}")
            except Exception as e:
                logger.warning(f"删除旧消息失败: {e}")

        # 发送图片（支持本地路径或 URL）
        try:
            message= await self.client.send_file(self.channel_name, pic, caption=message)
            logger.info(f'成功向TG发送消息，消息id={message.id}')
            return message
        except Exception as e:
            logger.warning(f'向TG发送消息失败：{e}')


# 假设 TGClient 已在别处定义并且有 async start() 方法
# from your_module import TGClient

_tg_clients: Dict[str, 'TGClient'] = {}
_tg_client_locks: Dict[str, asyncio.Lock] = {}
_tg_client_locks_lock = asyncio.Lock()  # 保护上面字典的并发访问

def _normalize_channel_name(channel_name: str) -> str:
    return channel_name if channel_name.startswith('@') else f'@{channel_name}'

async def get_tg_client(channel_name: str) -> 'TGClient':
    """
    根据 channel_name 获取或创建 TGClient 并启动（如果尚未启动）。
    并发安全：多个 task 同时请求同一 channel 时，只有一个会创建并 start()。
    """
    key = _normalize_channel_name(channel_name)

    # 快速无锁路径
    client = _tg_clients.get(key)
    if client:
        return client

    # 确保为该 key 拿到一个 per-key lock（使用全局锁创建它）
    async with _tg_client_locks_lock:
        lock = _tg_client_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _tg_client_locks[key] = lock

    # 在 per-key lock 内再次检查并可能创建 client
    async with lock:
        # 双重检查：其他 task 可能在我们获取锁前已创建
        client = _tg_clients.get(key)
        if client:
            return client

        # 下面是真正创建并 start() 的地方
        client = TGClient(channel_name=key)
        try:
            await client.start()
        except Exception:
            # 创建/启动失败：清理 per-key lock 以便后续重试（也可以记录日志）
            async with _tg_client_locks_lock:
                _tg_client_locks.pop(key, None)
            raise

        # 成功则缓存 client 并返回
        _tg_clients[key] = client
        return client


# 示例使用
async def main():
    # 示例：替换为你要使用的频道或用户（可以是 '@username' 或 channel id）
    channel = '@pancloudshare'
    tg_client = await get_tg_client(channel)

    # 搜索消息
    await tg_client.search_messages(search='#围猎', limit=1)

    # 示例：发送新消息并删除旧消息（如果需要）
    # await tg_client.send_messages_with_delete_old(
    #     pic='https://example.com/image.jpg',
    #     message='新的标题: 示例',
    #     is_delete_old=True,
    #     old_message_id=12345
    # )

if __name__ == '__main__':
    asyncio.run(main())
