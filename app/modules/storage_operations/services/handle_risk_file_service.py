import asyncio
from pathlib import Path

from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import MovieCloudInfo, Movie
from app.database.movie_repository import movie_repository
from app.modules.storage_operations.interfaces.cloud_disk_operator_interface import ICloudDiskOperator
from app.modules.storage_operations.interfaces.handle_risk_file_interface import IHandleRiskFile
from app.utils.obfuscate import obfuscate_title_pro


class HandleRiskFileService(IHandleRiskFile):

    async def _delete_risk_file(self, cloud_info: MovieCloudInfo, movie: Movie, cloud_operator: ICloudDiskOperator):
        dir_path=cloud_info.cloud_path
        pdir_file= await cloud_operator.get_dir(Path(dir_path))
        if pdir_file is None:
            return
        await cloud_operator.delete_file([pdir_file])

    @staticmethod
    async def _dir_rename(cloud_info:MovieCloudInfo,movie:Movie):

        cloud_info.cloud_path = movie.generate_path(is_obfuscate=True)



    async def handle_(self, cloud_info: MovieCloudInfo, movie: Movie, cloud_operator: ICloudDiskOperator):
        await self._delete_risk_file(cloud_info, movie, cloud_operator)
        await self._dir_rename(cloud_info, movie)
        cloud_info.share_link=None
        cloud_info.is_risk_share=False
        cloud_info.latest_episode_number=None
        cloud_info.save_suffixes
handle_risk_file_service = HandleRiskFileService()

async def main():
    from app.flow.sync_new_movie_flow import save_to_database

    setup_logging()
    await init_db()
    movie= await movie_repository.find_by_douban_id('36645835')
    r= await handle_risk_file_service.handle([movie])
    await save_to_database(r)
if __name__ == '__main__':
    asyncio.run(main())
