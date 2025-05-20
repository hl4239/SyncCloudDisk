import asyncio
import json
import re
from datetime import datetime

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

import Services.crawler_torrent.crawler
import settings
import utils
from QuarkDisk import QuarkDisk
from Services.alist_api import AlistAPI
from Services.aria2_api import Aria2API
from Services.crawler_torrent.bu_tai_lin_crawler import BuTaiLinCrawler
from Services.crawler_torrent.pan_dian_ying_shi_crawler import PanDianCrawler
from Services.download_torrent import DownloadTorrent
from Services.push_to_cloud_disk import PushToCloudDisk
from Services.episode_namer_dir.episode_namer import  EpisodeNamer
from Services.magnet_to_torrent import MagnetToTorrent
from database import engine
from models.resource import Resource, ResourceCategory


class SyncCloudDisk:
    def __init__(self,quark_disk:QuarkDisk,aria2api:Aria2API,alistapi:AlistAPI,crawler:BuTaiLinCrawler):

        self.quark_disk = quark_disk
        self.aria2_api = aria2api
        self.alist_api = alistapi
        self.crawler = crawler

    def remove_extension(self,filename):
        """
        去除文件名的后缀名

        参数:
            filename (str): 包含扩展名的文件名

        返回:
            str: 去除扩展名后的文件名
        """
        if '.' in filename:
            return filename[:filename.rindex('.')]
        return filename

    def splite_title(self,filename):
        """
        将title和年份分离，如你好(2025)->你好，2025
        :param filename:
        :return:
        """
        # 匹配格式：标题 + 空格 + 左括号 + 年份 + 右括号
        match = re.match(r'^(.*)\s*\((\d{4})\)$', filename)

        if match:
            title_no_year = match.group(1).strip()
            year = match.group(2)
            print("title_no_year:", title_no_year)
            print("Year:", year)
            return title_no_year,year
        else:
            print("No match found.")


    async def get_cloud_pdir(self,resource):
        """
        查询网盘对应的目录，如果不存在则创建
        :param resource:
        :return:
        """
        path=resource.cloud_storage_path
        try:
            pdir_fid = (await self.quark_disk.get_fids([path]))[0]['fid']
        except Exception:
            await self.quark_disk.mkdir(path)

            pdir_fid = (await self.quark_disk.get_fids([path]))[0]['fid']


        file_list = await self.quark_disk.ls_dir(pdir_fid)
        return pdir_fid, file_list








    async def get_need_sync_search_result_resource_list(self,search_result:Services.crawler_torrent.crawler.SearchResult,resource:Resource):
        """
        将爬取的资源进行命名格式化，然后与网盘存在的资源进行对比，找到需要更新的爬取的资源
        :param search_result:
        :param resource:
        :return:
        """
        crawler_episode_collection = [i.format_name for i in search_result.result]
        pdir_fid, file_list = await self.get_cloud_pdir(resource)
        cloud_episode_collection = [self.remove_extension(filename=['file_name']) for file in file_list]
        # 作差集找到网盘中不存在的集数
        not_exist_episode_num_list = EpisodeNamer.is_collection_episode_in_other_collection(cloud_episode_collection,
                                                                                            crawler_episode_collection)
        # 根据不存在的集数，找到需要更新的format_name
        wait_for_sync_episode_str_list = EpisodeNamer.find_collection_episode_by_list_num(not_exist_episode_num_list,
                                                                                          crawler_episode_collection)


        search_result_maps={
            i.format_name:i
            for i in search_result.result
        }
        result_list=[]
        for i in wait_for_sync_episode_str_list:
            result_list.append(search_result_maps[i])

        return result_list

    async def download_torrent(self,resource_list:list[Services.crawler_torrent.crawler.Resource],save_path):
        down=DownloadTorrent(self.aria2_api)
        for resource in resource_list:
            await  down.download_torrent(url=resource.url,path=save_path,name=f'{resource.format_name}.torrent')
        result_path_list= await down.get_downloaded()
        return result_path_list

    async def ensure_cloud_dir_empty(self,resource:Resource):
        """
        确保网盘目录存在且无torrent文件
        :return:
        """
        pdir_fid,file_list= await self.get_cloud_pdir(resource)
        remove_fid_list=[]
        for file in file_list:
            file_name=file['file_name']
            if file_name.endswith('.torrent'):
                remove_fid_list.append(file['fid'])
        if len(remove_fid_list)>0:
            await self.quark_disk.delete(remove_fid_list)



    async def start_async(self):
        with Session(engine) as session:
            statement = select(Resource).where(Resource.category == ResourceCategory.HOT_CN_DRAMA).order_by(
                Resource.douban_last_async.desc()).limit(settings.select_resource_num)
            results = session.exec(statement)
            resources = results.all()
            # resources=[resource for resource in resources if resource.title=='狮城山海(2025)']
            for resource in resources:
                douban_episode_update = resource.douban_last_episode_update
                cloud_disk_async_info = resource.cloud_disk_async_info
                if cloud_disk_async_info is None:
                    cloud_disk_async_info = {}
                cloud_disk_async_time = datetime.fromisoformat(
                    cloud_disk_async_info['last_async_time']) if cloud_disk_async_info.get('last_async_time') else None

                is_skip_update = cloud_disk_async_info.get('is_skip_update', False)
                is_force_update = cloud_disk_async_info.get('is_force_update', False)
                sync_status=cloud_disk_async_info.get('status', None)
                if (((cloud_disk_async_time is None) or (cloud_disk_async_time < douban_episode_update)) and is_skip_update == False and sync_status!='uploading') or is_force_update:
                    title = resource.title
                    pdir_path = resource.cloud_storage_path
                    total_episodes = resource.total_episodes
                    try:
                        search_result_ = await self.crawler.search(*self.splite_title(title))
                    except Exception as e:
                        utils.logger.error(f'{title}爬取资源发生错误：{str(e)}')
                        continue
                    downloaded_path_list= await self.download_torrent(search_result_.result,resource.storage_path)


                    await self.ensure_cloud_dir_empty(resource)

                    push_to_cloud = PushToCloudDisk(self.alist_api)

                    await push_to_cloud.push(downloaded_path_list,resource.cloud_storage_path )
                    task_list = push_to_cloud.task_list
                    utils.logger.info(json.dumps(task_list, indent=4, ensure_ascii=False))

                    cloud_disk_async_info.update({
                        'status':'uploading',
                        'task_list':task_list
                    })
                    resource.cloud_disk_async_info = cloud_disk_async_info
                    flag_modified(resource,'cloud_disk_async_info')
                    session.add(resource)
                    try:
                        session.commit()
                    except Exception as e:
                        print(e)

                    await asyncio.sleep(10)








async def main():
    quark_disk=QuarkDisk(settings.STORAGE_CONFIG['quark'][0])
    aria2=Aria2API()
    alistapi=AlistAPI()
    crawler=BuTaiLinCrawler()
    sync_cloud=SyncCloudDisk(quark_disk,aria2,alistapi,crawler)
    await sync_cloud.start_async()
    await quark_disk.close()
    await aria2.close()
    await alistapi.close()
    await crawler.close()

if __name__ == '__main__':
    asyncio.run(main())


