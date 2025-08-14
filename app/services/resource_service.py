import datetime
import logging
import re

from app.domain.models.resource import EpisodesInfo, Resource
from app.infrastructure.crawlers.them_movie_crawler import ThemMovieCrawler
from app.infrastructure.persistence.repositories.resource_repository import ResourceRepository
from app.services.episode_normalize_service import EpisodeNormalizeService

logger=logging.getLogger()
class ResourceService:
    def __init__(self,resource_repo:ResourceRepository,them_movie_crawler:ThemMovieCrawler,normalize_service:EpisodeNormalizeService):
        self.resource_repo=resource_repo

        self.them_movie_crawler=them_movie_crawler

        self.normalize_service=normalize_service

    async def get_latest_episodes_info(self,resource:Resource)->EpisodesInfo:
        """
        如果resource中的剧集信息是更新至xxx则爬取最新剧集，如果是xxx全则直接返回
        :param resource:
        :return:
        """
        result=None
        crawler_result=None
        if resource.episodes_info.is_finished():
            result=resource.episodes_info
        else :
            if resource.episodes_info.episodes_url is not None:
                crawler_result=await self.them_movie_crawler.get_detail_episode(resource.episodes_info.episodes_url)

        if result is None:

            crawler_result= await self.them_movie_crawler.search(f'{resource.get_title_without_year()} y:{resource.get_year()}')

            result=EpisodesInfo()
            result.total_episodes=crawler_result.total_episodes
            result.episodes_url=crawler_result.episodes_url

        return result

    async def update_episode_info(self, resource:Resource,episodes_info: EpisodesInfo):
        """
        对剧集信息更新，如果存在且更新则更新
        """
        exist_total_episode = resource.episodes_info.total_episodes
        to_add_total_episodes = episodes_info.total_episodes
        # 如果都有值，且待添加的更新就更新
        if exist_total_episode is not None and exist_total_episode != '' and (
                to_add_total_episodes is not None and to_add_total_episodes != ''):
            episode_normalized_list = await self.normalize_service.generate_name(
                [exist_total_episode, to_add_total_episodes])
            episode_normalized_maps = {
                i.original_name: i
                for i in episode_normalized_list
            }
            exist_normalized = episode_normalized_maps.get(exist_total_episode).normalized_name
            to_add_normalized = episode_normalized_maps.get(to_add_total_episodes).normalized_name
            exist_episode_num_list = self.normalize_service.normalized_name_to_num_list(exist_normalized)
            to_add_episode_num_list = self.normalize_service.normalized_name_to_num_list(to_add_normalized)
            if len(to_add_episode_num_list) > len(exist_episode_num_list):
                resource.episodes_info.total_episodes = to_add_total_episodes
                resource.episodes_info.last_update_time = datetime.datetime.now()


        elif (exist_total_episode is None or exist_total_episode == '') and (
                to_add_total_episodes is not None and to_add_total_episodes != ''):
            resource.episodes_info = episodes_info

            resource.episodes_info.last_update_time = datetime.datetime.now()




