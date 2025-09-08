import asyncio
import re
from logging import getLogger
from typing import List,  Tuple, Optional

from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import SplitTitleSeasonRegular
from app.modules.data_collection.interfaces.split_title_season_interface import ISplitTitleSeasonInterface
from app.utils.cache import async_ttl_cache

logger=getLogger(__name__)
class ASplitTitleSeasonService(ISplitTitleSeasonInterface):
    @staticmethod
    @async_ttl_cache(ttl=3600)
    def _split_title_season_1(title_season: str, patterns: List[str]) -> Tuple[str, Optional[str]]:
        """
        通用正则解析框架
        :param patterns: 正则表达式列表，每个必须至少有1个捕获组(title)和可选的第2个捕获组(season)
        :return: (title, season) - season 匹配不到返回 None
        """
        s = title_season.strip()

        for pattern in patterns:
            m = re.match(pattern, s, re.IGNORECASE)
            if m:
                # group(1) 是标题，group(2) 可选是季
                title = m.group(1).strip()
                season = m.group(2).strip() if m.lastindex and m.lastindex >= 2 else "第一季"
                logger.debug(f'title_season={title_season},被 {pattern} 捕获')
                return title, season

        # 如果所有正则都没匹配到
        raise RuntimeError(f'title_season={title_season} 为匹配到任何分割规则')

    @classmethod
    async  def _split_title_season(cls,title_season:str)-> tuple[str, str | None]:
        """
        从数据库获取分割规则，并分割
        :param title_season:
        :return:
        """
        regex_rules=[r.regular for r in await SplitTitleSeasonRegular.find_all().to_list()]

        title,season=cls._split_title_season_1(title_season, regex_rules)
        return title,season
    async def get_title(self,title_season:str,title_seasons:Tuple[str])->str:
        title,_=await self._split_title_season(title_season)
        return title

    async def get_season(self,title_season:str,title_seasons:Tuple[str])->str:
        _,season=await self._split_title_season(title_season)
        return season
a_split_title_season_service=ASplitTitleSeasonService()
async def main():
    setup_logging()
    await init_db()
    a=ASplitTitleSeasonService()
    title=await a.get_title(title_season='你好 第1季',title_seasons=('1','2'))
    season=await a.get_season(title_season='你好 第1季',title_seasons=('1','2'))
    logger.debug(title)
    logger.debug(season)
if __name__ == '__main__':
    asyncio.run(main())