import asyncio

from app.core.abc_aio_client import BaseAioClient


class TgBotClient(BaseAioClient):
    def __init__(self,chat_id,bot_token):
        super().__init__()
        self.init(
            name="TgBotClient",

        )
        self.chat_id = chat_id
        self.bot_token = bot_token
    async  def send_msg(self,text):
        data={
              "chat_id": self.chat_id,
              "text": text
            }

        r= await self.request(method="POST",path=f'https://api.telegram.org/bot{self.bot_token}/sendMessage',json=data)
        print(r)
    async def send_photo_description(self,pic_url,text):
        data = {
            "chat_id": self.chat_id,
            "photo": pic_url,
            "caption": text,
        }

        r = await self.request(method="POST",
                               path=f'https://api.telegram.org/bot{self.bot_token}/sendPhoto',
                               json=data)
        print(r)

tg_bot_client=TgBotClient(chat_id="@pancloudshare",bot_token="8425430691:AAEX0KeL6OU0hL9KNasy51IrzYopiLoQhkw")

async def main():
    await tg_bot_client.send_photo_description('https://img1.doubanio.com/view/photo/s_ratio_poster/public/p2921019240.webp','你好')
if __name__ == '__main__':
    asyncio.run(main())