import pytest

from app.domain.models.resource import TvCategory
from app.infrastructure.containers import container
from log import init_logging

init_logging()
@pytest.mark.asyncio
async def test_sync_cloud_disk():
    use_case1 = container.use_case1()
    await use_case1.sync_cloud_disk(['quark-4295','quark-7505','quark-4976'] ,TvCategory.HOT_CN_DRAMA)


@pytest.mark.asyncio
async def test_sync_cloud_disk1():
    use_case1 = container.use_case1()
    await use_case1.sync_cloud_disk(['quark-4295','quark-7505','quark-4976'],['藏海传(2025)'])



