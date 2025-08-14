from app.domain.models.cloud_file import CloudFile, ShareFile
from app.services.episode_normalize_service import EpisodeNormalizeService


class CloudFileService:
    def __init__(self,normalize_service:EpisodeNormalizeService):
        self.normalize_service = normalize_service
        pass

    def get_movie_files(self, cloud_files: list[CloudFile]) -> list[CloudFile]:
        """
        获取影视类文件（mp4, mkv, torrent）
        """
        if not cloud_files:
            return []

        video_exts = ('.mp4', '.mkv', '.torrent')
        result = []

        for cloud_file in cloud_files:
            if cloud_file.file_name and cloud_file.is_movie_file():
                result.append(cloud_file)

        return result

    async def get_normalized_files(self,cloud_files:list[CloudFile]) -> list[CloudFile]:
        if cloud_files is None:
            return []
        return [f for f in cloud_files if f.normalized_name is not None  ]



    async def normalize_episode(self,cloud_files:list[ShareFile]):
        """
        对分享文件进行标准化
        :param share_files:
        :return:
        """
        if cloud_files is None or len(cloud_files) == 0:
            return cloud_files

        share_file_name_maps={
            f.file_name:f
            for f in cloud_files
            if f.normalized_name is None and not f.normalize_invalid
        }

        r= await self.normalize_service.generate_name(list(share_file_name_maps.keys()))
        for i in r:
            f=share_file_name_maps[i.original_name]
            if i.is_valid:

                f.normalize_name(i.normalized_name)
            else:
                f.set_normalize_invalid()
        return cloud_files




