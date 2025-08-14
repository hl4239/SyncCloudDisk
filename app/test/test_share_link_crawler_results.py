import asyncio

import pytest
from sqlalchemy.sql.functions import count

from app.domain.models.resource import CloudDiskInfo
from app.domain.models.share_link_crawler_results import ShareLinkCrawlerResults


import pytest

from app.infrastructure.config import CloudAPIType
from app.infrastructure.containers import Container


@pytest.mark.asyncio
async def test_async_iteration():
    container=Container()
    crawler=container.share_link_crawler()
    results=await crawler.search('藏海传',num=2,cloud_type=CloudAPIType.QUARK)
    async for i in results:
        print(i)
    print(results.title)
    print('结束')








@pytest.mark.asyncio
async def test_sync_list():
    # 测试同步列表
    results = ShareLinkCrawlerResults(share_links=["linkA", "linkB"])

    links = [link async for link in results]
    assert links == ["linkA", "linkB"]