import datetime
import logging
from app.domain.models.resource import TvCategory, Resource, EpisodesInfo
from app.infrastructure.crawlers.douban_crawler import DouBanCrawler
from app.infrastructure.persistence.repositories.resource_repository import ResourceRepository
logger = logging.getLogger()
class TopMetaDataService:
    def __init__(self, resource_repo:ResourceRepository,douban_crawler:DouBanCrawler):
        self.resource_repo=resource_repo
        self.douban_crawler=douban_crawler
        pass
    async def get_top_meta_data(self,tv_type:TvCategory,count:int=20)->list[Resource]:
        """
        从豆瓣获取top榜元数据
        :param tv_type:
        :param count:
        :return:[Resource]
        """
        douban_response= await self.douban_crawler.get_hot_tv(tv_type,count=count)
        add_resource=[]
        for item in douban_response.subject_collection_items:
            resource=Resource()
            resource.title=f'{item.title}({item.year})'
            resource.description=item.comment
            resource.tv_category=tv_type
            resource.episodes_info=EpisodesInfo(total_episodes=item.episodes_info,last_update_time=datetime.datetime.now())
            resource.image_path=item.pic.large
            resource.subtitle=item.card_subtitle
            resource.tags=item.tags
            resource.last_metadata_update_time=datetime.datetime.now()
            add_resource.append(resource)

        return add_resource

    async def upsert(self,resources:list[Resource]):
        """
        如果存在则只对剧集信息更新，否则添加
        """

        _add_titles=[i.title for i in resources]
        exist_resources=self.resource_repo.get_by_titles(_add_titles)
        resource_maps={
            i.title:i
            for i in resources
        }
        exist_titles=[i.title for i in exist_resources]
        logger.debug(exist_resources)
        to_add_resources=[i for i in resources if i.title not in  exist_titles]
        to_update_resource=[]
        # 对已存在的进行剧集更新
        for exist_resource in exist_resources:
            to_add_resource=resource_maps.get(exist_resource.title)

            await exist_resource.update_episode_info(to_add_resource.episodes_info)

            exist_resource.last_metadata_update_time=datetime.datetime.now()

            to_update_resource.append(exist_resource)

        added_results= self.resource_repo.add_many(to_add_resources)
        updated_results=self.resource_repo.update_many(to_update_resource)
        self.resource_repo.session.commit()
        logger.info(f'已添加{len(added_results)}个 | 已更新{len(updated_results)}个')











