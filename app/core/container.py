from dependency_injector import containers, providers

from app.adapters.movie_data_source_adapter import MovieDataSourceAdapter
from app.database.movie_repository import MovieRepository
from app.modules.data_collection.container import DataCollectionContainer
from app.modules.data_collection.context import DataCollectionContext
from app.modules.episodes_filter.context import EpisodesFilterContext
from app.modules.link_parse.context import LinkParseContext
from app.modules.link_scraping.context import LinkScrapeContext
from app.services.open_ai_service import OpenAIService


class ProjectContainer(containers.DeclarativeContainer):
    # Repository（在项目级定义）
    movie_repository = providers.Factory(
        MovieRepository
    )
    open_ai_service=providers.Singleton(
        OpenAIService
    )
    data_collection_container=providers.Container(
        DataCollectionContainer,
        movie_repository=movie_repository,
        open_ai_service=open_ai_service,
    )
    data_collection_context=providers.Singleton(
        DataCollectionContext,
        container=data_collection_container
    )
    movie_data_source_adapter=providers.Factory(
        MovieDataSourceAdapter,
    )
    link_scrape_context=providers.Singleton(
        LinkScrapeContext
    )
    link_parse_context=providers.Singleton(
        LinkParseContext
    )
    episodes_filter_context=providers.Singleton(
        EpisodesFilterContext
    )

def wire_all(project_container):
    """集中定义 wire"""
    import app.modules.data_collection as data_collection
    project_container.data_collection_container().wire(
        modules=[data_collection]
    )