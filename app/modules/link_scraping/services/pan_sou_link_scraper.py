import asyncio
import logging


from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import Movie, MovieType, CloudType, CloudShareLink
from app.modules.link_scraping.clients.pan_sou_client import PanSouClient, pan_sou_client
from app.modules.link_scraping.interfaces.scraper_interface import ILinkScraper

from app.utils.async_iterator import AsyncCachedIterator

logger=logging.getLogger(__name__)
class PanSouLinkScraperService(ILinkScraper):
    def __init__(self, pan_sou_client:PanSouClient):
        self.pan_sou_client=pan_sou_client
    async def _fetch(self,movie:Movie,count:int,cloud_type:CloudType):
        if count<1:
            return []
        json_resp=await self.pan_sou_client.search(movie.title_season,[cloud_type])
        # 安全地访问嵌套字段，避免 KeyError
        link_dict = json_resp.get("data", {}).get("merged_by_type", {})
        first_key = next(iter(link_dict), None)
        if not first_key:
            return []
        link_infos = link_dict[first_key]
        if not link_infos:
            logger.info("no quark links for %s (response OK)", movie.title_season)
            return []

        results=[]
        link_infos=link_infos[:count]

        if isinstance(link_infos, list):
            for link_info in link_infos:
                url=link_info.get("url")
                password=link_info.get("password")
                title=link_info.get("note")
                results.append(CloudShareLink(url=url,title=title,share_password=password))
        else:
            logger.error("unexpected 'quark' structure for %s: %r", movie.title_season, link_infos)
        logger.debug(f'爬取title={movie.title_season}的{cloud_type}链接：{results}')
        return results

    async def search_quark(self, movie: Movie,count:int) -> AsyncCachedIterator[CloudShareLink]:
        return AsyncCachedIterator(await self._fetch(movie,count,CloudType.QUARK))

    async def search_baidu(self, movie: Movie, count: int) -> AsyncCachedIterator[CloudShareLink]:
        return AsyncCachedIterator(await self._fetch(movie, count,CloudType.BAIDU))


pan_sou_link_scraper_service    =PanSouLinkScraperService(pan_sou_client=pan_sou_client)

async def main() -> None:
    setup_logging()
    await init_db()
    result=await pan_sou_link_scraper_service.search(movies=[Movie(douban_id='赴山海',title_season='赴山海',movie_type=MovieType.TV),Movie(douban_id='生万物',title_season='生万物',movie_type=MovieType.TV)],count=5)

    for item in result:
        async for i in await item.quark_links:
            logger.debug(f'{i.title}{i.url}')
        async for i in await item.baidu_links:
            logger.debug(f'{i.title}{i.url}')

if __name__ == '__main__':
    asyncio.run(main())
