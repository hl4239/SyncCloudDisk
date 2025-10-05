import asyncio
import base64
import json
import logging
import re
from datetime import date

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from app.core.abc_aio_client import BaseAioClient
from app.utils.cache import async_ttl_cache


logger=logging.getLogger(__name__)
class RenRenClient(BaseAioClient):
    def __init__(self,):
        super().__init__()
        self.init(
            name="RenRenClient",

        )
    @async_ttl_cache(ttl=600)
    async def get_decrypt_secret(self):

        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'origin': 'https://m.yichengwlkj.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://m.yichengwlkj.com/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'Host': 'cdn.rrmj.plus',
            'Connection': 'keep-alive'
        }
        text= await self.fetch_text(method='get',path='https://cdn.rrmj.plus/c-next/mapp/1.9.14/_next/static/chunks/887-64dde9be9703f4bd.js',headers=headers)

        # 宽松模式（任意引号内内容）
        m2 = re.search(r'descryptSecret\s*[:=]\s*["\']([^"\']+)["\']', text)
        if m2:
            return m2.group(1)

    @classmethod
    def decrypt_data(cls,ciphertext_b64: str, key: str) -> dict:
        """
        解密函数，对应于你 JS 里的 P(e, t)

        :param ciphertext_b64: Base64 编码的 AES 密文
        :param key: 解密密钥 (字符串)
        :return: 解密后的 JSON 对象 (dict)
        """
        # AES 密钥：需要是 16/24/32 字节
        key_bytes = key.encode("utf-8")

        # Base64 解码
        cipher_bytes = base64.b64decode(ciphertext_b64)

        # 初始化 AES 解密器（ECB 模式）
        cipher = AES.new(key_bytes, AES.MODE_ECB)

        # 解密 + 去掉 PKCS7 填充
        decrypted = unpad(cipher.decrypt(cipher_bytes), AES.block_size)

        # 转换为字符串再解析 JSON
        return json.loads(decrypted.decode("utf-8"))
    async def get_date_movies(self,target_date:date):

        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Origin': 'https://m.yichengwlkj.com',
            'Pragma': 'no-cache',
            'Referer': 'https://m.yichengwlkj.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'aliId': '7F6EF02A-512A-4BB3-B0BD-BA6F2DBAD92F',
            'clientType': 'web_pc',
            'clientVersion': '1.0.0',
            'ct': 'web_pc',
            'cv': '1.0.0',
            'deviceId': '7F6EF02A-512A-4BB3-B0BD-BA6F2DBAD92F',
            'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            't': '1758952167869',
            'token': '',
            'uet': '9',
            'umid': '7F6EF02A-512A-4BB3-B0BD-BA6F2DBAD92F',
            'x-ca-sign': 'svlOIMw+2Vrkiz6IhtMSfsc9yDuAZW9psoGvvmsjWcY=',
            'Host': 'api.rrmj.plus',
            'Cookie': 'HWWAFSESTIME=1758953968889; HWWAFSESID=d59b7827443eb57a06'
        }
        page=1
        page_size=10
        text=await self.fetch_text(method="get", path=f"https://api.rrmj.plus/m-station/schedule/play/date/query?playShowDate={target_date.strftime("%Y-%m-%d")}&page={page}&rows={page_size}", headers= headers)
        try:

            r=  self.decrypt_data(text,await self.get_decrypt_secret())
            result_data=[]
            result_data.extend(r['data']['content'])
            total=r['data']['total']
            for i in range((total//page_size)):
                page+=1
                text = await self.fetch_text(method="get",
                                             path=f"https://api.rrmj.plus/m-station/schedule/play/date/query?playShowDate={target_date.strftime("%Y-%m-%d")}&page={page}&rows={page_size}",
                                             headers=headers)
                r = self.decrypt_data(text,await self.get_decrypt_secret())
                result_data.extend(r['data']['content'])
            return result_data
        except Exception as e:
            logger.error(f'renren client error: {e}',exc_info=True)
        return None
renren_client=RenRenClient()


async def main():
    r= await renren_client.get_date_movies(date(2025,10,10))
    print(r)
# 示例
if __name__ == "__main__":
    asyncio.run(main())