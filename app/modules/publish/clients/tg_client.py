import asyncio
import logging
import os
from typing import Optional, Dict
from telethon import TelegramClient

# ---------- 新增：通用路径工具 ----------
def local_path(filename: str) -> str:
    """
    获取与当前文件同目录下的指定文件路径。
    例如 local_path('mydata.db') => /path/to/this_script/mydata.db
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, filename)


# ----------------------------------------

logger = logging.getLogger(__name__)
API_ID = int(os.getenv('TG_API_ID', '611335'))
API_HASH = os.getenv('TG_API_HASH', 'd524b414d21f4d37f08684c1df41ac9c')

class TGClient:
    def __init__(self, channel_name: str, session_name: Optional[str] = None):
        self.channel_name = channel_name
        self.session_name = session_name or f'user_session_{channel_name.strip("@")}'
        # 修改点：session 文件也放在当前目录下，保证一致
        session_path = local_path(self.session_name)
        self.client = TelegramClient(session_path, API_ID, API_HASH)

    async def start(self):
        await self.client.start()

    async def search_messages(self, search: str = '你好', limit: int = 5):
        async for message in self.client.iter_messages(self.channel_name, search=search, limit=limit):
            print(f"ID: {message.id}, 文本: {message.text}")

    async def send_messages_with_delete_old(
        self,
        pic: str,
        message: str,
        is_delete_old: bool = False,
        old_message_id: Optional[int] = None
    ):
        if is_delete_old and old_message_id is not None:
            try:
                await self.client.delete_messages(self.channel_name, old_message_id)
                logger.info(f"Deleted old message id={old_message_id}")
            except Exception as e:
                logger.warning(f"删除旧消息失败: {e}")

        try:
            message = await self.client.send_file(self.channel_name, pic, caption=message)
            logger.info(f'成功向TG发送消息，消息id={message.id}')
            return message
        except Exception as e:
            logger.warning(f'向TG发送消息失败：{e}')

    async def send_message(self, message: str):
        await self.client.send_message(self.channel_name, message)


_tg_clients: Dict[str, 'TGClient'] = {}
_tg_client_locks: Dict[str, asyncio.Lock] = {}
_tg_client_locks_lock = asyncio.Lock()

def _normalize_channel_name(channel_name: str) -> str:
    return channel_name if channel_name.startswith('@') else f'@{channel_name}'

async def get_tg_client(channel_name: str) -> 'TGClient':
    key = _normalize_channel_name(channel_name)
    client = _tg_clients.get(key)
    if client:
        return client

    async with _tg_client_locks_lock:
        lock = _tg_client_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _tg_client_locks[key] = lock

    async with lock:
        client = _tg_clients.get(key)
        if client:
            return client

        client = TGClient(channel_name=key)
        try:
            await client.start()
        except Exception:
            async with _tg_client_locks_lock:
                _tg_client_locks.pop(key, None)
            raise

        _tg_clients[key] = client
        return client

async def main():
    channel = '@pancloudshare'
    tg_client = await get_tg_client(channel)
    await tg_client.search_messages(search='#围猎', limit=1)
    await tg_client.send_message('Nihao')

if __name__ == '__main__':
    asyncio.run(main())
