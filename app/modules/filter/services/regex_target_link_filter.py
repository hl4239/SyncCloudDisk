import asyncio
import logging
import re
from typing import List

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
    # 内部定义正则模板，其中 `{title}` 是占位符
    _regex_templates = [
        r"^{title}.*",                # 标题必须从开头匹配
        r".*【{title}】.*",           # 标题被【】包裹
        r".*{title}.*1080p.*",        # 标题后面带 1080p
        r".*{title}.*S\d{{2}}E\d{{2}}" , # 标题后跟美剧 SxxExx 格式
        r".*《{title}》.*",
        r".*「{title}」.*"
    ]

    @classmethod
    def _build_patterns(cls, movie_title_season: str):
        """根据 movie_title_season 生成对应的正则 Pattern 列表"""
        patterns = []
        for template in cls._regex_templates:
            regex = template.format(title=re.escape(movie_title_season))
            patterns.append(re.compile(regex, re.IGNORECASE))
        return patterns

    @classmethod
    def _is_target(cls, link_title: str, movie_title_season: str) -> bool:
        """
        判断 link_title 是否符合针对 movie_title_season 动态生成的 regex
        """
        patterns = cls._build_patterns(movie_title_season)

        for pattern in patterns:
            if pattern.search(link_title):
                logger.debug(
                    f'匹配成功: '
                    f'link_title="{link_title}" '
                    f'movie_title_season="{movie_title_season}" '
                    f'pattern="{pattern.pattern}"'
                )
                return True

        logger.debug(
            f'未匹配: '
            f'link_title="{link_title}" '
            f'movie_title_season="{movie_title_season}" '
            f'patterns={[p.pattern for p in patterns]}'
        )
        return False
    async def get_target_links(self, movie: Movie, link_parses: AsyncCachedIterator[LinkParse]):
        movie_title_season = movie.title_season

        async for link in link_parses:
            if self._is_target(link.link.title, movie_title_season=movie_title_season):
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
