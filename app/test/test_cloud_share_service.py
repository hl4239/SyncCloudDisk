import asyncio

import pytest

from app.infrastructure.containers import Container, container
from app.services.cloud_share_service import CloudShareService
from log import init_logging

init_logging()


@pytest.mark.asyncio
async def test_parse():
    container = Container()
    cloud_share_service = container.cloud_share_service()
    f = await cloud_share_service.get_parse_info('https://pan.quark.cn/s/c787f7f6c951')
    f = await cloud_share_service.get_parse_info('https://pan.quark.cn/s/c787f7f6c951')
    print(f)

@pytest.mark.asyncio
async def test_get_parse_info():

    cloud_share_service = container.cloud_share_service()
    tasks=[cloud_share_service.get_parse_info('https://pan.quark.cn/s/280ce774c57f',is_normalize=True) for _ in range(3)]
    await asyncio.gather(*tasks)




