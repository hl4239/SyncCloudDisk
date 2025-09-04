from typing import Tuple

from app.core.logging_config import get_logger
from app.modules.data_collection.interfaces.split_title_season_interface import ISplitTitleSeasonInterface
from app.modules.data_collection.services.a_split_title_season_service import ASplitTitleSeasonService
from app.modules.data_collection.services.b_split_title_season_service import BSplitTitleSeasonService

logger=get_logger(__name__)
class FallbackSplitTitleSeasonService(ISplitTitleSeasonInterface):
    def __init__(self,a_split_title_season_service:ASplitTitleSeasonService,b_split_title_season_service:BSplitTitleSeasonService):
        self.a_split_title_season_service = a_split_title_season_service
        self.b_split_service = b_split_title_season_service

    async def get_title(self, target_title_season: str, title_seasons: Tuple[str]) -> str:
        title=None
        try:
            title=await self.a_split_title_season_service.get_title(target_title_season, title_seasons)
        except Exception as e:
            logger.warning(e)
            try:
                title=await self.b_split_service.get_title(target_title_season, title_seasons)
            except Exception as e:
                logger.warning(e)
                logger.warning(f'获取title失败，title_season={target_title_season}失败，将返回None')
        logger.debug(f'获取title_season={target_title_season}的title={title}')
        return title

    async def get_season(self, target_title_season: str, title_seasons: Tuple[str]) -> str:
        season=None
        try:
            season = await self.a_split_title_season_service.get_season(target_title_season, title_seasons)
        except Exception as e:
            logger.warning(e)
            try:
                season = await self.b_split_service.get_season(target_title_season, title_seasons)
            except Exception as e:
                logger.warning(e)
                logger.warning(f'获取season失败，title_season={target_title_season}失败，将返回None')
        logger.debug(f'获取title_season={target_title_season}的season={season}')
        return season