import asyncio

from telethon import TelegramClient
from telethon.tl.types import InputMessagesFilterPhotos

api_id= "611335"
api_hash= "d524b414d21f4d37f08684c1df41ac9c"
chanel_name='@pancloudshare'


async def search_messages_without_admin():
    async with TelegramClient('user_session', api_id, api_hash) as client:
        await client.start()

        # 只进行文本搜索，不指定用户
        print("搜索包含 'hello' 的消息:")
        async for message in client.iter_messages(chanel_name, search='你好', limit=5):
            print(f"ID: {message.id}, 文本: {message.text}")
            await message.edit('hello')

            # 搜索图片消息
        from telethon.tl.types import InputMessagesFilterPhotos
        print("\n搜索图片消息:")
        async for message in client.iter_messages(chanel_name, filter=InputMessagesFilterPhotos, limit=5):
            print(f"ID: {message.id}, 有图片: {message.photo is not None}")


