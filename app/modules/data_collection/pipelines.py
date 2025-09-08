# file: app/data_collector.py
import asyncio
from typing import List, Dict, Optional

from app.database.models import TVCategory
from app.modules.data_collection.interfaces.current_episodes_provider_interface import ICurrentEpisodesProvider
from app.modules.data_collection.interfaces.movie_base_provider_interface import IMovieBaseProvider
from app.modules.data_collection.interfaces.total_episodes_provider_interface import ITotalEpisodesProvider
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.modules.data_collection.services.a_tmdb_id_provider_service import TMDBIDProviderService
from app.utils.pipeline import Pipeline, pipeline_task  # 你现有的链式 Pipeline



class DataCollectorPipeline:
    def __init__(self,movie_base_provider:IMovieBaseProvider,
                 current_episodes_provider:ICurrentEpisodesProvider,
                 total_episodes_provider:ITotalEpisodesProvider,
                 tmdb_id_provider:TMDBIDProviderService):
        # 两条独立的 pipeline，互不干扰
        self.pipeline = Pipeline()
        # 注册并绑定任务
        self.pipeline.register_from(self)
        self.movie_base_provider = movie_base_provider
        self.current_episodes_provider = current_episodes_provider
        self.total_episodes_provider = total_episodes_provider
        self.tmdb_id_provider = tmdb_id_provider

    # ---------------- Popular pipeline ----------------

    @pipeline_task(name='entry_hot', order=0, batch=False)
    async def _entry_hot(self, categories:List[TVCategory],count: int = 10)->List[MovieDataSourceResult]:
        return await self.movie_base_provider.get_hot_movies(categories,count)
    @pipeline_task(name='entry_1', order=0, batch=False)
    async def _entry_search(self, keyword:str,count:int=5)->List[MovieDataSourceResult]:
        ...
    @pipeline_task(name='fetch_tmdb_id', order=10, batch=False,provides=('tmdb_infos',))
    async def _fetch_tmdb_id(self,movie_data_sources:List[MovieDataSourceResult])->List[MovieDataSourceResult]:
        ...
    @pipeline_task(name='fetch_current_episodes', order=20, batch=False)
    async def _fetch_current_episodes(self,movie_data_sources:List[MovieDataSourceResult])->List[MovieDataSourceResult]:
        ...
    @pipeline_task(name='fetch_total_episodes', order=30, batch=False,provides=('total_episodes',))
    async def _fetch_total_episodes(self,movie_data_sources:List[MovieDataSourceResult])->List[MovieDataSourceResult]:
        ...


    # ---------------- 公共运行接口 ----------------
    async def run_hot(self, categories:List[TVCategory],count: int = 10) -> List[MovieDataSourceResult]:
        """
        异步调用：运行热门资源流水线并返回最终 model
        """
        result = await self.pipeline.run("entry_hot", categories, count)
        # pipeline.run 返回最终 model（entry 返回的 model 经过每步修改后返回）
        return result

    async def run_search(self,keyword:str,count:int=5) -> List[MovieDataSourceResult]:
        """
        异步调用：运行基于 title 的搜索流水线并返回最终 model
        """
        result = await self.pipeline.run("entry_search", keyword, count)
        return result

    # 方便的同步包装（在非异步环境中调用）
    def run_hot_sync(self, limit: int = 10) -> List[MovieDataSourceResult]:
        return asyncio.run(self.run_hot(limit))

    def run_search_sync(self, title: str, limit: int = 10) -> List[MovieDataSourceResult]:
        return asyncio.run(self.run_search(title, limit))


# ---------------- 使用示例 ----------------
if __name__ == "__main__":
    dp = DataCollectorPipeline()

    # 同步方式运行热门资源流水线
    popular_model = dp.run_hot_sync(limit=5)

    # 同步方式运行搜索流水线
    search_model = dp.run_search_sync("Matrix", limit=3)
