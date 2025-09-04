import pytest

from app.database.database import init_db, init_db_sync
from app.database.models import TVCategory
from app.modules.data_collection.container import DataCollectionContainer
init_db_sync()
@pytest.mark.asyncio
async def test_get_hot_movies():
    container=DataCollectionContainer()
    await container.init_resources()
    movie_data_source_service=await container.movie_base_provider_service()
    res= await movie_data_source_service.get_hot_movies([TVCategory.CHINA,TVCategory.KOREA],10)
    for r in res:
        if r.title is None:
            print('none')
        print(await r.title_season)
