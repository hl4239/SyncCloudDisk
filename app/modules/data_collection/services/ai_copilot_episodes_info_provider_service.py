import asyncio
import datetime
import logging
from typing import List

from agents import Runner

from app.database.models import EpisodesInfo, MovieType
from app.modules.data_collection.interfaces.episodes_air_date_provider_interface import IEpisodesAirDateProvider
from app.modules.data_collection.interfaces.episodes_air_time_provider_interface import IEpisodesAirTimeProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.modules.data_collection.services.tmdb_air_date_provider_service import tmdb_air_date_provider
from app.services.movie_service import movie_service
from app.services.open_ai_service import OpenAIService, open_ai_service
from app.utils.cache import async_ttl_cache
from app.utils.lazy_load import lazy

logger=logging.getLogger(__name__)
class AICopilotEpisodesInfoProvider(IEpisodesAirDateProvider,IEpisodesAirTimeProvider):
    def __init__(self, open_ai_service:OpenAIService):
        self.open_ai_service = open_ai_service


    async def _get_ai_agent_air_date(self):
        instruction = """
        你是一位影视剧追剧日历专家，你将从我提供的title_season,description确定一个影视剧，并搜寻其剧集播出日历
        【输出格式要求】
        输出必须严格遵循以下JSON结构,确保用markdown···json格式包裹文字：
        [
            {
              "air_date":"字符串类型，格式如：'2025-09-17T20:00:00+08:00'"
              "episode_number": "int类型，必需字段，如1、2、3,分别代表第一集、第二集、第三集"
            }
        ]
        """
        return await self.open_ai_service.get_agent( instructions=instruction)


    async def _get_ai_agent_air_time(self):
        instruction = """
        你是一位影视剧追剧日历专家，你将从我提供的title_season,description确定一个影视剧，并补充我给出的剧集播放时间表episodes_info
        补充说明：其中air_date是我已经确定绝对正确的日期，你需要做的是对air_time补充
        【输出格式要求】
        输出必须严格遵循以下JSON结构,确保用markdown···json格式包裹文字：
        [
            {
              "air_time":"字符串类型 格式为'hh:mm:ss'，时区为北京时间(utc+8)"
              "episode_number": "int类型，必需字段，如1、2、3,分别代表第一集、第二集、第三集"
            }
        ]
        """
        return await self.open_ai_service.get_agent( instructions=instruction)



    async def get_air_time(self, movie_data_source: MovieDataSourceResult) -> List[EpisodesInfo]:
        if await movie_data_source.movie_type == MovieType.MOVIE:
            return []

        episodes_info=await movie_data_source.episodes_info
        title_season=await movie_data_source.title_season

        if not episodes_info:
            logger.warning(f"title_season={title_season} No episodes info found 无法使用ai_copilot来补充air_time")
            return episodes_info
        if movie_service.is_air_time_full(episodes_info) or  movie_service.is_finale(episodes_info):
            logger.info(f'{title_season}无需填充air_time')
            return episodes_info

        agent = await self._get_ai_agent_air_time()
        description=await movie_data_source.description
        result = await Runner.run(agent, input=f'title_season={title_season} description={description} episodes_info_list={[e for e in episodes_info if e]}' )
        for i in range(3):
            try:
                json_resp = self.open_ai_service.format_to_json(result.final_output)
                logger.debug(f'ai对air_time补充：{json_resp}')


                episodes_info_episode_number_map={
                    e.episode_number:e
                for e in episodes_info
                }
                for r in json_resp:
                    air_time_str=r['air_time']
                    episode_number=r['episode_number']
                    episodes_info_item=episodes_info_episode_number_map[episode_number]
                    episodes_info_item.air_time=air_time_str

                return episodes_info
            except Exception as e:
                logger.exception(f'发送了错误,重试第{i+1}/3次 :{e}')
        return episodes_info

    async def get_air_date(self, movie_data_source: MovieDataSourceResult) -> List[EpisodesInfo]:
        agent = await self._get_ai_agent_air_date()
        title_season=await movie_data_source.title_season
        description=await movie_data_source.description
        result = await Runner.run(agent, input=f'title_season={title_season} description={description}')
        json_resp = self.open_ai_service.format_to_json(result.final_output)
        logger.debug(f'ai搜寻的追剧日历信息：{json_resp}')
        return json_resp

ai_copilot_episodes_air_time_provider = AICopilotEpisodesInfoProvider(open_ai_service=open_ai_service)
ai_copilot_episodes_air_time_provider=ai_copilot_episodes_air_time_provider
async def main():
    from app.database.database import init_db
    from app.core.logging_config import setup_logging

    await init_db()
    setup_logging()
    import tmdbsimple as tmdb
    from app.core.config import settings

    tmdb.API_KEY =settings.TMDB_API_KEY
    movie_data_source=MovieDataSourceResult()
    movie_data_source.title_season=lazy('与晋长安')
    movie_data_source.description=lazy('上个世纪上海法租界一所西式洋房里，最初住着一户姓林的人家。30年代初，林家败落，房子被有心人买下，改建成一所妇产医院，在这所医院里，发生了许多故事。50年代初，新中国成立，这座洋房又成为工厂车间，工作和来往着工人、技术人员等。90年代初，这所老洋房成为商住两用房，来来往往的人们又发生了新的故事。')
    movie_data_source.episodes_info=lazy(lambda :tmdb_air_date_provider._fetch_infos(253093,1))
    episodes_info_result=  await  ai_copilot_episodes_air_time_provider.get_air_time(movie_data_source=movie_data_source)
    print(episodes_info_result)
if __name__ == '__main__':
    asyncio.run(main())