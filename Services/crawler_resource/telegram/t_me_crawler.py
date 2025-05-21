import asyncio

import aiohttp


class TMeCrawler:
    def __init__(self,t_me_url:str) -> None:
        self.session=aiohttp.ClientSession()
        self.t_me_url=t_me_url
    async def request(self,method,url,params=None,json=None,data=None,headers=None):

        await self.session.request(method=method,url=url,params=params,json=json,data=data,headers=headers)



    async def search_telegram(self,keyword:str):

        params = {
            'q':keyword,
        }
        async  with await self.session.request(method='get',url=self.t_me_url,params=params) as resp:
            text = await resp.text()
            return text


async def main():
    crawler=TMeCrawler('https://t.me/s/ucquark')
    await crawler.search_telegram('折腰')
if __name__ == '__main__':
    asyncio.run(main())