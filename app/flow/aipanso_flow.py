import asyncio

import tmdbsimple
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.task_registry import registry
from app.database.database import init_db
from app.flow.sync_new_movie_flow import save_new_movies_metadata_to_database
from app.modules.new_movie_metadata_collector.services.aipanso_provider_service import \
    aipanso_new_movie_provider_service


class PP1(BaseModel):
    ...
@registry.register(name="爱盘搜专用分享链接生成", params_model=PP1)
async def get_today_new_movie_metadata(params:PP1,progress_callback, log_callback):
    new_movies= await aipanso_new_movie_provider_service.get_today_new_movie_metadata()
    progress_callback(50)
    movies= await save_new_movies_metadata_to_database(new_movies)
    progress_callback(100)
    print([m.title_season for m in movies])
    return [m.title_season for m in movies]

async def main():
    await init_db()
    setup_logging()
    tmdbsimple.API_KEY=settings.TMDB_API_KEY
    await get_today_new_movie_metadata(params=PP1(),progress_callback=lambda a:...,log_callback=lambda a:...)
if __name__ == '__main__':
    asyncio.run(main())