import asyncio
from typing import Any, Coroutine

import aiohttp
from aiohttp import ClientSession
from requests import session

from models.resource import ResourceCategory


class CrawlerDouban:
    def __init__(self):
        self.session:aiohttp.ClientSession =None
        self.base_url='https://frodo.douban.com'
    def _init(self):
        headers = {
            'user-agent':'Rexxar-Core/0.1.3 api-client/1 com.douban.frodo/7.98.0(318) Android/28 product/M391Q vendor/MEIZU model/M391Q brand/MEIZU  rom/flyme4  network/wifi  udid/342316168c4c576021f1836339d6dd47a78a45b9  platform/mobile com.douban.frodo/7.98.0(318) Rexxar/1.2.151  platform/mobile 1.2.151'
        }
        self.session = aiohttp.ClientSession(
            headers=headers,
        )
    async def __aenter__(self):
        self._init()
        return self
    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    async   def get_hot_tv(self,tv_type:ResourceCategory):
        url=''
        params={}
        if tv_type==ResourceCategory.HOT_CN_DRAMA:
            params={
                    'playable': '0',
                    'start': '0',
                    'count': '20',
                    'udid': '342316168c4c576021f1836339d6dd47a78a45b9',
                    'rom': 'flyme4',
                    'apikey': '0dad551ec0f84ed02907ff5c42e8ec70',
                    's': 'rexxar_new',
                    'channel': 'Baidu_Market',
                    'timezone': 'Asia/Shanghai',
                    'device_id': '342316168c4c576021f1836339d6dd47a78a45b9',
                    'os_rom': 'flyme4',
                    'sugar': '0',
                    'loc_id': '108288',
                    '_sig': '+USKTbukOV+f5oTj1EKy4US1aFw=', # URL解码后的值
                    '_ts': '1745652498'
                }
            url='/api/v2/subject_collection/tv_domestic/items'
        elif tv_type==ResourceCategory.HOT_US_EU_DRAMA:
            params={
                    'playable': '0',
                    'start': '0',
                    'count': '20',
                    'udid': '342316168c4c576021f1836339d6dd47a78a45b9',
                    'rom': 'flyme4',
                    'apikey': '0dad551ec0f84ed02907ff5c42e8ec70',
                    's': 'rexxar_new',
                    'channel': 'Baidu_Market',
                    'timezone': 'Asia/Shanghai', # %2F 被解码成了 /
                    'device_id': '342316168c4c576021f183636d9d47a78a45b9',
                    'os_rom': 'flyme4',
                    'sugar': '0',
                    'loc_id': '108288',
                    '_sig': 'AW5I71bx9kiabl4FMhQlZTFRTso=', # %3D 被解码成了 =
                    '_ts': '1745598097'
                }
            url='/api/v2/subject_collection/tv_american/items'
        elif tv_type==ResourceCategory.HOT_KR_DRAMA:
            params={
                    'playable': '0',
                    'start': '0',
                    'count': '20',
                    'udid': '342316168c4c576021f1836339d6dd47a78a45b9',
                    'rom': 'flyme4',
                    'apikey': '0dad551ec0f84ed02907ff5c42e8ec70',
                    's': 'rexxar_new',
                    'channel': 'Baidu_Market',
                    'timezone': 'Asia/Shanghai', # %2F 被解码成了 /
                    'device_id': '342316168c4c576021f1836339d6dd47a78a45b9',
                    'os_rom': 'flyme4',
                    'sugar': '0',
                    'loc_id': '108288',
                    '_sig': 'tTTyNDRR1aeYgpgA2qs9Po7HAww=', # %3D 被解码成了 =
                    '_ts': '1745598444'
                }
            url='/api/v2/subject_collection/tv_korean/items'
        elif tv_type==ResourceCategory.HOT_JP_DRAMA:
            params={
                    'playable': '0',
                    'start': '0',
                    'count': '20',
                    'udid': '342316168c4c576021f1836339d6dd47a78a45b9',
                    'rom': 'flyme4',
                    'apikey': '0dad551ec0f84ed02907ff5c42e8ec70',
                    's': 'rexxar_new',
                    'channel': 'Baidu_Market',
                    'timezone': 'Asia/Shanghai', # %2F 被解码成了 /
                    'device_id': '342316168c4c576021f1836339d6dd47a78a45b9',
                    'os_rom': 'flyme4',
                    'sugar': '0',
                    'loc_id': '108288',
                    '_sig': 'j414HcvEIiBKkWsRPDHMThwQWzY=', # %3D 被解码成了 =
                    '_ts': '1745598415'
                }
            url='/api/v2/subject_collection/tv_japanese/items'
        elif tv_type==ResourceCategory.HOT_ANIME:
            params={
                    'playable': '0',
                    'start': '0',
                    'count': '20',
                    'udid': '342316168c4c576021f1836339d6dd47a78a45b9',
                    'rom': 'flyme4',
                    'apikey': '0dad551ec0f84ed02907ff5c42e8ec70',
                    's': 'rexxar_new',
                    'channel': 'Baidu_Market',
                    'timezone': 'Asia/Shanghai',
                    'device_id': '342316168c4c576021f1836339d6dd47a78a45b9',
                    'os_rom': 'flyme4',
                    'sugar': '0',
                    'loc_id': '108288',
                    '_sig': 'oVn32qX5K7PeOFN5M4e3TfJutvQ=',
                    '_ts': '1745598494'
                }
            url='/api/v2/subject_collection/tv_animation/items'
        else:
            return None
        async with  self.session.request(url=self.base_url+url,params=params,method='GET')as resp:
            try:
                resp_json = await resp.json()
                return resp_json

            except Exception as e:
                print(e)
                return None






async def main():
    async with CrawlerDouban() as session:
        result=await  session.get_hot_tv('domestic')
        print(result)
if __name__ == '__main__':
   asyncio.run(main())