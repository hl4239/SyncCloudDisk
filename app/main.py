# 项目主入口
import asyncio

import tmdbsimple

import app
#
#
from app.core.config import settings
from app.core.container import ProjectContainer, wire_all
from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.modules.data_collection.flow import data_collection_get_hot_flow

project_container:ProjectContainer=None
async def init_app():
    global project_container
    setup_logging()
    await init_db()
    tmdbsimple.API_KEY=settings.TMDB_API_KEY
    project_container=  ProjectContainer()
    project_container.data_collection_container().wire(modules=[app])

    await project_container.data_collection_container().init_resources()
    # wire_all(project_container)
    # await project_container.data_collection_container().shutdown_resources()



async def main():
    await init_app()
    data_collection_context = project_container.data_collection_context()
    await data_collection_get_hot_flow('asdas')
    await project_container.data_collection_container().shutdown_resources()
if __name__ == '__main__':
    asyncio.run(main())
