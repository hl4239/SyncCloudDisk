import pytest

from app.domain.models.resource import TvCategory
from app.infrastructure.containers import Container, container
from app.services.top_meta_data_service import TopMetaDataService
from log import init_logging


init_logging()




@pytest.mark.asyncio
async def test_upsert():
    service = container.top_meta_data_service()
    resources = await service.get_top_meta_data(tv_type=TvCategory.HOT_CN_DRAMA, count=20)
    await service.upsert(resources)
    assert True
