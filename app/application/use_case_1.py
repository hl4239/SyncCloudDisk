import asyncio
import logging

from multipledispatch import dispatch
from sqlalchemy.util import await_only

from app.domain.models.resource import TvCategory, CloudDiskInfo, Account, Resource, EpisodesInfo
from app.domain.models.share_link_crawler_results import ShareLinkCrawlerResults
from app.infrastructure.config import settings, CloudAPIType
from app.infrastructure.crawlers.share_link_crawler import ShareLinkCrawler
from app.infrastructure.persistence.repositories.resource_repository import ResourceRepository
from app.services.cloud_disk_service import CloudDiskService
from app.services.cloud_share_service import CloudShareService
from app.services.resource_service import ResourceService
from app.services.sync_from_share_service import SyncFromShareService

from app.services.top_meta_data_service import TopMetaDataService

logger=logging.getLogger()
class UseCase1:
    def __init__(self, top_meta_service:TopMetaDataService,cloud_disk_service:CloudDiskService,cloud_share_service:CloudShareService,
                 share_link_crawler:ShareLinkCrawler,resource_repo:ResourceRepository,resource_service:ResourceService,
                 sync_from_share_service:SyncFromShareService,):
        self.top_meta_service = top_meta_service
        self.cloud_disk_service = cloud_disk_service
        self.share_link_crawler = share_link_crawler
        self.resource_repo = resource_repo
        self.cloud_share_service = cloud_share_service
        self.resource_service = resource_service
        self.sync_from_share_service = sync_from_share_service
    async def sync_top_meta_data(self,tv_cate:TvCategory,count:int):
        """
        同步top榜
        :param tv_cate:
        :param count:
        :return:
        """
        resources= await self.top_meta_service.get_top_meta_data(tv_cate,count)
        await self.top_meta_service.upsert(resources)




    async def _sync_cloud_disk(self,name_type,share_links_reserved:list[str],share_link_crawler_results:ShareLinkCrawlerResults,latest_episode:EpisodesInfo,cloud_disk_info_account:Account):
        try:
            if not cloud_disk_info_account.is_sync_finish:
                await self.cloud_disk_service.mkdir(path=cloud_disk_info_account.cloud_storage_path,name_type=name_type)
                await asyncio.sleep(3)
                share_links_reserved.extend(cloud_disk_info_account.last_sync_share_links)
                sync_share_links=[]
                is_synced_latest=False
                for share_link in share_links_reserved:

                    new_files = await self.sync_from_share_service.sync_new_file(name_type,
                                                                                 cloud_disk_info_account.cloud_storage_path,
                                                                                 share_link,
                                                                                 False,
                                                                                )
                    if len(new_files) > 0:
                        sync_share_links.append(share_link)
                    logger.info(f'✅{name_type}从{share_link}更新了{[f.file_name for f in new_files]}')
                    is_synced_latest=await self.sync_from_share_service.is_synced_latest(name_type,cloud_disk_info_account.cloud_storage_path,latest_episode.total_episodes)
                    if is_synced_latest:
                        break
                if not is_synced_latest:
                    async  for share_link in share_link_crawler_results:

                        new_files = await self.sync_from_share_service.sync_new_file(name_type,
                                                                                     cloud_disk_info_account.cloud_storage_path,
                                                                                     share_link,
                                                                                     False,
                                                                                     )
                        if len(new_files) > 0:
                            sync_share_links.append(share_link)
                        logger.debug(f'✅{name_type}从{share_link}更新了{[f.file_name for f in new_files]}')
                        is_synced_latest =await self.sync_from_share_service.is_synced_latest(name_type,
                                                                                         cloud_disk_info_account.cloud_storage_path,
                                                                                         latest_episode.total_episodes)
                        if is_synced_latest:
                            break


                cloud_disk_info_account.set_is_sync_finish(is_synced_latest and latest_episode.is_finished())
                cloud_disk_info_account.last_sync_share_links = sync_share_links
                logger.info(f'✅{name_type}-更新完毕-{cloud_disk_info_account}')
                return cloud_disk_info_account
            else:
                logger.info(f'{name_type}-{cloud_disk_info_account.cloud_storage_path}已更新完结，无需更新')
        except Exception as e:
            logger.error(f'❌更新{name_type}-时出错：{e}')

    @dispatch(list, list,str)
    async def sync_cloud_disk(self,name_types:list[str],resources:list[Resource],n:str=None):
        """

        :param name_types:
        :param resources:
        :param n: 仅用于dispatch的标识
        :return:
        """
        share_link_crawl_count = settings.share_link_crawl_count
        for resource in resources:
            share_link_crawler_results=await self.share_link_crawler.search(resource.get_title_without_year(),share_link_crawl_count,CloudAPIType.QUARK)
            cloud_disk_info_account_maps={
                f.name:f
                for f in resource.cloud_disk_info.accounts
            }
            latest_episode=await self.resource_service.get_latest_episodes_info(resource)
            await resource.update_episode_info(latest_episode)
            share_links_reserved=[]
            if resource.cloud_disk_info.last_sync_share_link is not None:
                share_links_reserved.append(resource.cloud_disk_info.last_sync_share_link)
            tasks = []
            for name_type in name_types:
                cloud_disk_info_account=cloud_disk_info_account_maps.get(name_type,None)
                if cloud_disk_info_account is None:
                    cloud_disk_info_account=Account.default_factory(name=name_type, cloud_storage_path=resource.get_default_cloud_path())
                    resource.cloud_disk_info.accounts.append(cloud_disk_info_account)
                task=  self._sync_cloud_disk(name_type,
                                      share_links_reserved=share_links_reserved,
                                      share_link_crawler_results=share_link_crawler_results,
                                      latest_episode=latest_episode,
                                      cloud_disk_info_account=cloud_disk_info_account
                                      )
                tasks.append(task)
            await asyncio.gather(*tasks)





        self.resource_repo.update_many(resources)
        self.resource_repo.session.commit()


    @dispatch(list, list)
    async def sync_cloud_disk(self,name_types:list[str],titles:list[str]):
        resources=self.resource_repo.get_by_titles(titles)
        await self.sync_cloud_disk(name_types, resources,'')

    @dispatch(list, TvCategory)
    async def sync_cloud_disk(self,name_types:list[str],tv_cate:TvCategory):
        """

        :param name_types:
        :param tv_cate:
        :return:
        """

        resources=self.resource_repo.get_by_category(tv_cate,settings.select_resource_count)
        await self.sync_cloud_disk(name_types,resources,'')



