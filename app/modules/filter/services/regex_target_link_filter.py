import asyncio
import logging
import re
from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import Movie, MovieType
from app.modules.filter.interfaces.target_link_filter_interface import ITargetLinkFilter
from app.modules.link_parse.flow import link_parse_flow_parses
from app.modules.link_parse.schemas import LinkParseResult, LinkParse, PrepareParseLinks
from app.modules.link_scraping.flow import link_scrape_flow_search
from app.utils.async_iterator import AsyncCachedIterator

logger=logging.getLogger(__name__)
class RegexTargetLinkFilter(ITargetLinkFilter):

    @staticmethod
    def _normalize(title: str) -> str:
        """
        标准化标题：
        - 转小写
        - 去掉空格和常见分隔符（【】()[]-_等）
        """
        # 只保留中文、英文、数字
        clean = re.sub(r"[^\w\u4e00-\u9fa5]", "", title)
        return clean.lower()

    @classmethod
    def _is_target(cls, link_title: str, movie_title_season: str) -> bool:
        """
        判断 link_title 是否对应 movie_title_season
        规则：标准化后，要求 link_title 必须从开头匹配 movie_title_season
        """
        link_norm = cls._normalize(link_title)
        movie_norm = cls._normalize(movie_title_season)

        # 正则：必须从开头开始匹配
        pattern = re.compile(rf"^{re.escape(movie_norm)}")
        result = bool(pattern.search(link_norm))

        logger.debug(
            f'判断是否为目标影视对应网盘资源的结果：'
            f'link_title_norm={link_norm} '
            f'movie_title_norm={movie_norm} '
            f'pattern={pattern.pattern} '
            f'result={result}'
        )
        return result
    async def get_target_links(self,movie:Movie,link_parses:AsyncCachedIterator[LinkParse] ):
        logger.debug('开始过滤目标link')
        movie_title_season=movie.title_season

        async for link in link_parses:
            if self._is_target(link.link.title,movie_title_season=movie_title_season):
                yield link


regex_target_link_filter = RegexTargetLinkFilter()
async def main():
    setup_logging()
    await init_db()
    scrape_result= await  link_scrape_flow_search([Movie(douban_id='赴山海',title_season='赴山海',movie_type=MovieType.TV),Movie(douban_id='生万物',title_season='生万物',movie_type=MovieType.TV)],count=5)
    parse_results=await link_parse_flow_parses([PrepareParseLinks(movie=i.movie,scrape_quark_links=i.quark_links) for i in scrape_result])
    filter_result=await regex_target_link_filter.filter(parse_results)

    for item in filter_result:
        async for i in  item.quark_parses:
            print(i.link.title,i.link.url)
    filter_result=await regex_target_link_filter.filter(parse_results)

    for item in filter_result:
        async for i in  item.quark_parses:
            print(i.link.title,i.link.url)

if __name__ == '__main__':
    asyncio.run(main())
