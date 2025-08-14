from dependency_injector import containers, providers
from importlib_metadata.compat.py39 import normalized_name
from sqlmodel import create_engine, Session

from app.application.use_case_1 import UseCase1
from app.infrastructure.cloud_storage.cloud_api_factory import CloudAPIFactory
from app.infrastructure.config import  Settings, load_config
from app.infrastructure.crawlers.ai_pan_so_crawler import AiPanSoCrawler
from app.infrastructure.crawlers.douban_crawler import DouBanCrawler
from app.infrastructure.crawlers.them_movie_crawler import ThemMovieCrawler
from app.infrastructure.persistence.repositories.resource_repository import ResourceRepository
from app.infrastructure.persistence.repositories.task_repository import InMemoryTaskRepository

from app.services import cloud_file_service
from app.services.cloud_disk_service import CloudDiskService
from app.services.cloud_file_service import CloudFileService
from app.services.cloud_share_service import CloudShareService
from app.services.episode_normalize_service import EpisodeNormalizeService

from app.services.public_episode_normalize_service import PublicEpisodeNormalizeService
from app.services.resource_service import ResourceService
from app.services.sync_from_share_service import SyncFromShareService
from app.services.task_service import TaskService
from app.services.top_meta_data_service import TopMetaDataService

class Container(containers.DeclarativeContainer):


    # 配置项
    config = providers.Singleton(
        load_config
    )

    # 数据库引擎 (Singleton)
    engine = providers.Singleton(
        create_engine,
        url=config().database.url,
        echo=config().database.echo
    )

    # 数据库会话工厂 (Factory)
    session_factory = providers.Factory(
        Session,
        bind=engine
    )

    # 豆瓣爬虫 (Resource管理生命周期)
    douban_crawler = providers.Singleton(
        DouBanCrawler
    )

    them_movie_crawler = providers.Singleton(
        ThemMovieCrawler
    )

    # 资源仓库 (Factory)
    resource_repo = providers.Factory(
        ResourceRepository,
        session=session_factory
    )

    # 元数据服务 (Factory)
    top_meta_data_service = providers.Factory(
        TopMetaDataService,
        resource_repo=resource_repo,
        douban_crawler=douban_crawler
    )
    episode_normalized_service = providers.Factory(
        PublicEpisodeNormalizeService,
    )
    resource_service = providers.Factory(
        ResourceService,
        resource_repo=resource_repo,
        them_movie_crawler=them_movie_crawler,
        normalize_service=episode_normalized_service
    )

    cloud_api_factory = providers.Factory(CloudAPIFactory)





    cloud_file_service = providers.Factory(
        CloudFileService,
        normalize_service=episode_normalized_service,
    )
    cloud_disk_service = providers.Singleton(
        CloudDiskService, config=config().cloud_api, cloud_api_factory=cloud_api_factory,
        cloud_file_service=cloud_file_service,
    )
    cloud_share_service=providers.Singleton(
        CloudShareService,
        normalize_service=episode_normalized_service
        ,
    )




    share_link_crawler = providers.Singleton(
        AiPanSoCrawler
    )
    sync_from_share_service=providers.Factory(
        SyncFromShareService,
        cloud_disk_service=cloud_disk_service,
        cloud_share_service=cloud_share_service,
        normalize_service=episode_normalized_service,
        cloud_file_service=cloud_file_service,
    )
    task_repository=providers.Singleton(
    InMemoryTaskRepository

    )

    use_case1=providers.Factory(UseCase1,
                                top_meta_service=top_meta_data_service,
                                cloud_disk_service=cloud_disk_service,
                                share_link_crawler=share_link_crawler,
                                resource_repo=resource_repo,
                                cloud_share_service=cloud_share_service,
                                resource_service=resource_service,
                                sync_from_share_service=sync_from_share_service,
                                )
    task_service = providers.Singleton(TaskService

                                       ,
                                       repository=task_repository,
                                       use_case=use_case1)
async def init_singleton(container):
    await container.douban_crawler().init()
    await container.them_movie_crawler().init()
    await container.cloud_disk_service().init()
    await container.share_link_crawler().init()

container = Container()

