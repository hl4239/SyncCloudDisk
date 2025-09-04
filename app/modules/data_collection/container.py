
import asyncio


from app.modules.data_collection.clients.douban_client import DoubanClient

from dependency_injector import containers, providers
import logging

from app.modules.data_collection.interfaces.current_episodes_provider_interface import ICurrentEpisodesProvider
from app.modules.data_collection.interfaces.match_to_database_interface import IMatchToDatabase
from app.modules.data_collection.interfaces.movie_base_provider_interface import IMovieBaseProvider
from app.modules.data_collection.interfaces.total_episodes_provider_interface import ITotalEpisodesProvider
from app.modules.data_collection.pipelines import DataCollectorPipeline
from app.modules.data_collection.services.a_split_title_season_service import ASplitTitleSeasonService
from app.modules.data_collection.services.b_split_title_season_service import BSplitTitleSeasonService
from app.modules.data_collection.services.douban_mapper_service import DoubanMapperService
from app.modules.data_collection.services.douban_movie_data_provider_service import DoubanMovieBaseProviderService
from app.modules.data_collection.services.fallback_split_title_season_service import FallbackSplitTitleSeasonService
from app.modules.data_collection.services.match_to_database_service import MatchToDatabaseService
from app.modules.data_collection.services.tmdb_episodes_provider_service import TMDBEpisodesProviderService
from app.modules.data_collection.services.tmdb_id_provider_service import TMDBIDProviderService

# 方式1: 使用 async generator 创建资源
async def create_douban_client():
    """创建并初始化 DoubanClient 资源"""
    client = DoubanClient()
    await client.init()
    try:
        yield client
    finally:
        await client.shutdown()
async def create_movie_base_provider(
    douban_client: DoubanClient,
    mapper: DoubanMapperService
) -> IMovieBaseProvider:
    # 这里 douban_client 已经是初始化好的实例
    return DoubanMovieBaseProviderService(douban_client=douban_client, mapper=mapper)

class DataCollectionContainer(containers.DeclarativeContainer):
    """数据采集模块的依赖注入容器"""
    movie_repository = providers.Dependency()

    open_ai_service=providers.Dependency()
    # 方式1: 使用 async generator
    douban_client = providers.Resource(
        create_douban_client
    )
    douban_mapper_service=providers.Factory(
        DoubanMapperService
    )
    movie_base_provider_service= providers.Resource(
        create_movie_base_provider,
        douban_client=douban_client,
        mapper=douban_mapper_service
    )
    tmdb_id_provider_service=providers.Singleton(
        TMDBIDProviderService
    )
    current_episodes_provider_service:ICurrentEpisodesProvider = providers.Singleton(
        TMDBEpisodesProviderService,


    )
    total_episodes_provider_service:ITotalEpisodesProvider = providers.Singleton(
        TMDBEpisodesProviderService,

    )
    match_to_database_service:IMatchToDatabase = providers.Singleton(
        MatchToDatabaseService,
        movie_repo=movie_repository,
    )
    data_collection_pipelines:DataCollectorPipeline=providers.Singleton(
        DataCollectorPipeline,
        movie_base_provider=movie_base_provider_service,
        current_episodes_provider=current_episodes_provider_service,
        total_episodes_provider=total_episodes_provider_service,
    tmdb_id_provider=tmdb_id_provider_service
    )
    a_split_title_season_service=providers.Singleton(
        ASplitTitleSeasonService,
    )
    b_split_title_season_service=providers.Singleton(
        BSplitTitleSeasonService,
        open_ai_service=open_ai_service
    )
    split_title_season_service=providers.Singleton(
        FallbackSplitTitleSeasonService,
        a_split_title_season_service=a_split_title_season_service,
        b_split_title_season_service=b_split_title_season_service
    )



async def main():
    container=DataCollectionContainer()
    await container.init_resources()
    douban_client: DoubanClient =await container.douban_client()
    # res= await douban_client.get_hot_tv(TVCategory.CHINA,1)

    await container.shutdown_resources()
if __name__ == '__main__':
    asyncio.run(main())


