import asyncio
import logging

import uvicorn

from app.application.use_api import app
from app.domain.models.resource import TvCategory
from app.infrastructure.containers import Container, container
from app.interfaces import tasks_api

from log import init_logging

init_logging()

async def async_main():

    use_case1=container.use_case1()
    # await use_case1.sync_cloud_disk(['quark-4295','quark-4976','quark-7505'],TvCategory.HOT_CN_DRAMA)
    await use_case1.sync_cloud_disk(['quark-4295'], ['七根心简(2025)'])
def main():
    asyncio.run(async_main())

if __name__ == '__main__':
    # main()
    uvicorn.run(app, host="0.0.0.0", port=8000)