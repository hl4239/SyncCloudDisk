import asyncio

import aiohttp
from lxml import html

from Services.metadata_crawler.crawler import ResourceMetadata, SearchResults


class ThemMovieCrawler:
    def __init__(self, ):

        self.session=aiohttp.ClientSession()
        self.base_url='https://www.themoviedb.org'
    async def __aenter__(self):

        return self
    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()
    async def request(self,method,url,json=None,data=None,params=None,headers=None):

        await self.session.request(method,url,json=json,data=data,params=params,headers=headers)

    async def _search(self,keyword):
        url=f'{self.base_url}/search'
        params={
            'query':keyword,
            'language':'zh-CN',
        }
        async with self.session.get(url,params=params) as response:
            text = await response.text()
            return text

    def _parse_search(self,text):
        tree = html.fromstring(text)

        # XPath: 精确按 class 层级匹配，并提取 <a> 的 href 属性
        hrefs = tree.xpath('//div[@class="title"]'
                           '//a[@class="result"]/@href')
        target_href = hrefs[0]
        return target_href
    async def search(self,keyword):
        try:
            text=await self._search(keyword)
            detail_url= self._parse_search(text)
            detail_text= await self.get_detail(detail_url)
            resource_metadata= await self.parse_detail_text(detail_text)
            search_result= SearchResults(title=keyword,resource_metadata=resource_metadata)
        except Exception as e:
            raise Exception(f'影视数据库搜索{keyword}发生错误 error:{e}')from e
        return search_result
    async def parse_detail_text(self,detail_text):
        tree = html.fromstring(detail_text)
        t1=tree.xpath('//section[contains(@class,"panel") and contains(@class,"season")]'
                                  '//div[@class="content"]'
                                  '//h2'
                                  '//a[@href]')[0]
        current_season=t1.text_content().strip().replace(' ','')
        episodes_url=t1.get('href')
        text= await self.get_detail_episode(episodes_url)
        latest_episode=await self.parse_detail_episode(text)


        resource_metadata=ResourceMetadata(latest_episode=latest_episode,episodes_url=episodes_url)
        return resource_metadata
    async def parse_detail_episode(self,text):
        tree = html.fromstring(text)

        # XPath: 精确按 class 层级匹配，并提取 <a> 的 href 属性
        hrefs = tree.xpath('//div[contains(@class, "episode") and contains(@class, "closed") and .//span[contains(@class, "runtime")]]')
        for t in hrefs:
            latest_episode = t.xpath('.//span[@class="episode_number"]/text()')[0]
            latest_episode = str(f"更新至{latest_episode}集")
        return latest_episode

    async def get_detail_episode(self,episode_url):
        async with self.session.get(self.base_url+episode_url) as response:
            text = await response.text()
            return text

    async def get_detail(self,url):

        async with self.session.get(f'{self.base_url}{url}') as response:
            text = await response.text()
            return text
async def main():
    crawler=ThemMovieCrawler()
    await crawler.search('藏海传')
if __name__ == '__main__':
    asyncio.run(main())