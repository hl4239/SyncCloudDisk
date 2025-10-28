import asyncio

from app.database.database import init_db
from app.database.models import Movie
from app.flow.sync_new_movie_flow import save_to_database


async def init_cloud_path():
    movies = await Movie.find_all().to_list()
    for movie in movies:
        for cloud_info in movie.cloud_infos:
            cloud_info.cloud_path = movie.generate_path()
    await save_to_database(movies)

async def main():
    await init_db()

    await init_cloud_path()

if __name__ == '__main__':
    asyncio.run(main())