import asyncio
import json
from typing import  List

from agents import Runner

from app.core.logging_config import setup_logging, get_logger
from app.database.database import init_db
from app.modules.data_collection.interfaces.split_title_season_interface import ISplitTitleSeasonInterface
from app.services.interfaces.open_ai_interface import IOpenAIService
from app.services.open_ai_service import OpenAIService, open_ai_service
from app.utils.cache import async_ttl_cache
from app.utils.lazy_load import Lazy, lazy

logger=get_logger(__name__)
class BSplitTitleSeasonService(ISplitTitleSeasonInterface):
    def __init__(self,open_ai_service:IOpenAIService):
        self.open_ai_service=open_ai_service

    async def _get_ai_agent(self):
        instruction="""
        你是一位影视媒体库分类专家，你将从我提供的{title_season_list}中提取出各个title_season所对应的title,season'
        【输出格式要求】
        输出必须严格遵循以下JSON结构,确保用markdown···json格式包裹文字：
        [
            {
              "title_season":"字符串类型，必需字段，代表输入的title_season"
              "title":"字符串类型，必需字段，代表提取后的title,如果你没有提取到，则返回原始title_season"
              "season": "字符串类型，必需字段，代表提取后的season,如果你没有提取到，则返回空字符串"
            },
        ]
        """
        return await self.open_ai_service.get_agent(instructions=instruction)

    # 缓存60秒，因为会批量title_season一次性交给ai生成后缓存60秒
    @async_ttl_cache(ttl=600)
    async def _split_title_season_1(self,title_seasons:List[str]):
        agent=await self._get_ai_agent()
        for i in range(3):
            try:
                result = await Runner.run(agent, input=f'{json.dumps(title_seasons,indent=2,ensure_ascii=False)}')
                json_resp=self.open_ai_service.format_to_json(result.final_output)
                logger.debug(f'ai对title_season的分割结果：{ json_resp}')
                return json_resp
            except Exception as e:
                logger.exception(f'发送了错误,重试第{i+1}/3次 :{e}')
        return []


    async def _split_title_season(self,target_title_season:str,title_seasons:List[str]):

        json_results=await self._split_title_season_1(title_seasons)
        for json_result in json_results:

            try:
                title = json_result['title']
                season = json_result['season']
                title_season=json_result['title_season']
                if target_title_season == title_season:
                    if not season:
                        season='第一季'
                    return title, season
            except KeyError as e:
                raise KeyError(f'ai分割title_seasons={title_seasons}响应格式错误，exception={e}')
        raise Exception(f'未在ai的响应结果中匹配到title_season={target_title_season}')

    async def get_title(self, target_title_season: Lazy[str], title_seasons: List[Lazy[str]]) -> str:
        title_seasons=[await i for i in title_seasons]
        title,_=await self._split_title_season(await target_title_season,title_seasons)
        return title

    async def get_season(self, target_title_season: Lazy[str], title_seasons: List[Lazy[str]]) -> str:
        title_seasons = [await i for i in title_seasons]
        _,season = await self._split_title_season(await target_title_season, title_seasons)
        return season

async def main():
    await init_db()
    setup_logging()
    open_ai_service=OpenAIService()
    b_=BSplitTitleSeasonService(open_ai_service=open_ai_service)
    title=  await b_.get_title(target_title_season=lazy('重启之极海听雷2'),title_seasons=[lazy('你好'),lazy('重启之极海听雷2'),lazy('凡人修仙传：重返天南'),])
    season= await b_.get_season(target_title_season=lazy('重启之极海听雷2'),title_seasons=[lazy('你好'),lazy('重启之极海听雷2'),lazy('凡人修仙传：重返天南'),]                  )
    print(title,season)
b_split_title_season_service=BSplitTitleSeasonService(open_ai_service)
if __name__ == '__main__':
    asyncio.run(main())