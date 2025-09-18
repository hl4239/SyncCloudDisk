import asyncio
import logging

from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import Movie, CloudShareLink, MovieType, TMDBInfos
from app.modules.filter.interfaces.target_link_filter_interface import ITargetLinkFilter
from app.modules.filter.services.regex_target_link_filter import regex_target_link_filter
from app.modules.link_parse.flow import link_parse_flow_parses
from app.modules.link_parse.schemas import LinkParseResult, LinkParse, ShareFile, PrepareParseLinks
from app.modules.link_scraping.flow import link_scrape_flow_search
from app.utils.async_iterator import AsyncCachedIterator

logger=logging.getLogger(__name__)
class OnlyOneMovieFilter(ITargetLinkFilter):
    """
    只包含一种影视资源，不存在合集
    """

    async def is_only_one_movie(self,share_folder:ShareFile):
        """
        当前文件夹如果只有1个文件夹没用其它文件则递归遍历
        如果有多个文件夹，返回false
        如果是空文件夹，返回false
        如果是文件夹与文件混合，如果不含有剧集范围文件夹，否则返回false
        如果只含文件，返回True
        :param share_folder:
        :return:
        """
        files=await share_folder.children
        if len(files)==0:
            logger.debug(f'only one movie filter: 文件夹为空，返回false')
            return False

        if len(files)==1 and files[0].is_folder:
            return await self.is_only_one_movie(files[0])
        if len(files)>1:
            has_folder=False
            for file in files:
                if file.is_folder and (await file.standardized).is_valid:
                    logger.debug(f'only one movie filter: 含有混合文件，且存在剧集范围文件夹:{file.name}，返回true')
                    return True
                if file.is_folder:
                    has_folder=True
            if not has_folder:
                logger.debug('only one movie filter :当前文件夹只有文件，返回true')
                return True
        logger.debug(f'only one movie filter:不符合任何条件，返回false')
        return False

    async def get_target_links(self,movie:Movie,link_parses:AsyncCachedIterator[LinkParse]):
        async for link_parse in link_parses:
            is_target=await self.is_only_one_movie(link_parse.root)
            if is_target:
                yield link_parse
only_one_movie_filter = OnlyOneMovieFilter()
async def main():
    setup_logging()
    await init_db()
    scrape_result= await  link_scrape_flow_search([Movie(douban_id='赴山海',title_season='赴山海',movie_type=MovieType.TV,tmdb_infos=TMDBInfos(season_number=1)),Movie(douban_id='生万物',title_season='生万物',movie_type=MovieType.TV,tmdb_infos=TMDBInfos(season_number=1))],count=5)
    parse_results=await link_parse_flow_parses([PrepareParseLinks(movie=i.movie,scrape_quark_links=i.quark_links) for i in scrape_result])
    filter_result=await only_one_movie_filter.filter(parse_results)

    for item in filter_result:
        async for i in  item.quark_parses:
            print(i.link.title,i.link.url)


if __name__ == '__main__':
    asyncio.run(main())
