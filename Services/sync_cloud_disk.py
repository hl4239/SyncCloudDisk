import asyncio
import copy
import json
import re
from datetime import datetime

from litellm.files.main import file_list
from sqlalchemy import false
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

import Services.crawler_resource.crawler
import settings
import utils
from QuarkDisk import QuarkDisk
from Services.alist_api import AlistAPI
from Services.aria2_api import Aria2API
from Services.crawler_resource.crawler import ResourceQuark
from Services.crawler_resource.telegram.uc_quark_crawler import TMeUCQuarkCrawler
from Services.download_torrent import DownloadTorrent
from Services.episode_namer_dir.episode_namer import  EpisodeNamer
from Services.episode_namer_dir.public_episode_namer import PublicEpisodeNamer
from Services.quark_share_dir_tree import QuarkShareDirTree
from database import engine
from models.resource import Resource, ResourceCategory


class SyncCloudDisk:
    def __init__(self,quark_disk:QuarkDisk,aria2api:Aria2API,alistapi:AlistAPI,crawler:TMeUCQuarkCrawler):

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


    async def get_cloud_pdir(self,path,ls_dir=True):
        """
        查询网盘对应的目录，如果不存在则创建
        :param ls_dir:
        :param resource:
        :return:
        """

        try:
            pdir_fid = (await self.quark_disk.get_fids([path]))[0]['fid']
        except Exception:
            await self.quark_disk.mkdir(path)

            pdir_fid = (await self.quark_disk.get_fids([path]))[0]['fid']
        file_list=None
        if ls_dir:
            file_list = await self.quark_disk.ls_dir(pdir_fid)

        return pdir_fid, file_list








    async def get_need_sync_list(self,search_result:Services.crawler_resource.crawler.SearchResult,resource:Resource)->ResourceQuark:
        """
        将爬取的资源与网盘存在的资源进行对比，找到需要更新的爬取的资源,
        :param search_result:
        :param resource:
        :return:
        """
        crawler_episode_collection = [i.format_name for i in search_result.result[0].file_list]
        pdir_fid, file_list = await self.get_cloud_pdir(resource.cloud_storage_path)
        cloud_episode_collection = [(await PublicEpisodeNamer.generate_name([file['file_name']]))[0].format_name for file in file_list if file['file_type']!=0]
        # 作差集找到网盘中不存在的集数

        not_exist_episode_num_list = EpisodeNamer.is_collection_episode_in_other_collection(cloud_episode_collection,
                                                                                            crawler_episode_collection)
        # 根据不存在的集数，找到需要更新的format_name
        wait_for_sync_episode_str_list = EpisodeNamer.find_collection_episode_by_list_num(not_exist_episode_num_list,
                                                                                          crawler_episode_collection)


        search_result_maps={
            i.format_name:i
            for i in search_result.result[0].file_list
        }
        result_list=[]
        for i in wait_for_sync_episode_str_list:
            result_list.append(search_result_maps[i])
        new_r=copy.deepcopy(search_result.result[0])
        new_r.file_list=result_list
        return new_r



    async def ensure_cloud_dir_empty(self,resource:Resource):
        """
        确保网盘目录存在且无torrent文件
        :return:
        """
        pdir_fid,file_list= await self.get_cloud_pdir(resource.cloud_storage_path)
        remove_fid_list=[]
        for file in file_list:
            file_name=file['file_name']
            if file_name.endswith('.torrent'):
                remove_fid_list.append(file['fid'])
        if len(remove_fid_list)>0:
            await self.quark_disk.delete(remove_fid_list)

    async def save_to_cloud(self,resource_quark:ResourceQuark,resource:Resource):
        fid_list=[i.fid for i in resource_quark.file_list]
        share_fid_token_list=[i.share_fid_token for i in resource_quark.file_list]


        to_pdir_fid,_= await self.get_cloud_pdir(resource.cloud_storage_path,ls_dir=False)
        quark_dir_tree=QuarkShareDirTree.get_quark_share_tree(resource_quark.url)
        stoken=quark_dir_tree.ParseQuarkShareLInk.stoken
        pwd_id=quark_dir_tree.ParseQuarkShareLInk.pwd_id
        title=resource.title
        to_pdir_path=resource.cloud_storage_path
        share_link=resource_quark.url
        try:
            await  self.quark_disk.save_file(fid_list=fid_list,
                                           fid_token_list=share_fid_token_list,
                                           to_pdir_fid=to_pdir_fid, stoken=stoken,
                                           pwd_id=pwd_id)
            utils.logger.info(f'{title}|{share_link}✅转存{[i.format_name for i in resource_quark.file_list]}到{to_pdir_path}成功')
            await asyncio.sleep(3)
            _,file_list_=await self.get_cloud_pdir(resource.cloud_storage_path,ls_dir=True)
            file_maps_={
                file['file_name']:file['fid']
                for file in file_list_
            }

            # 改名
            for quark_file in resource_quark.file_list:
                fid= file_maps_.get(quark_file.file_name)
                suffix=quark_file.file_name.split('.')[-1]
                new_name=f'{quark_file.format_name}.{suffix}'
                if fid is not None:
                    resp= await self.quark_disk.rename(fid,new_name)
                    await asyncio.sleep(1)

        except Exception as e:

            utils.logger.error(f'{title}|{share_link}❌转存失败，抛出异常：{str(e)}')

    async def is_next_need_update(self,latest_episode:str,path):
        """
        与全网更新的剧集对比，判断是否有剧集缺少
        :return:
        """

        _,file_list=await self.get_cloud_pdir(path)
        cloud_episode_liste=[
            i.format_name
            for i in await PublicEpisodeNamer.generate_name([
                file['file_name']
                for file in file_list
            ])
        ]
        all_episodes=(await PublicEpisodeNamer.generate_name([latest_episode]))[0].format_name
        not_exist=PublicEpisodeNamer.is_collection_episode_in_other_collection(cloud_episode_liste,[all_episodes])
        return len(not_exist)==0


    async def start_async(self):
        with Session(engine) as session:
            statement = select(Resource).where(Resource.category == ResourceCategory.HOT_CN_DRAMA).order_by(
                Resource.douban_last_async.desc()).limit(settings.select_resource_num)
            results = session.exec(statement)
            resources = results.all()
            # resources=[resource for resource in resources if resource.title=='狮城山海(2025)']
            for resource in resources:
                douban_episode_update = resource.douban_last_episode_update
                if resource.cloud_disk_async_info is None:
                    resource.cloud_disk_async_info={}
                cloud_disk_async_info = resource.cloud_disk_async_info
                if cloud_disk_async_info is None:
                    cloud_disk_async_info = {}
                cloud_disk_async_time = datetime.fromisoformat(
                    cloud_disk_async_info['last_async_time']) if cloud_disk_async_info.get('last_async_time') else None

                is_skip_update = cloud_disk_async_info.get('is_skip_update', False)
                is_force_update = cloud_disk_async_info.get('is_force_update', False)
                need_update=cloud_disk_async_info.get('need_update', False)
                total_episodes=resource.total_episodes
                if ((((cloud_disk_async_time is None) or (cloud_disk_async_time < douban_episode_update) or (need_update==True)) and is_skip_update == False ) or is_force_update)and (total_episodes!=''and total_episodes is not None):
                    title = resource.title
                    pdir_path = resource.cloud_storage_path
                    total_episodes = resource.total_episodes
                    try:
                        search_result_ = await self.crawler.search(*self.splite_title(title))
                    except Exception as e:
                        utils.logger.error(f'{title}爬取资源发生错误：{str(e)}')
                        continue
                    resource_quark= await self.get_need_sync_list(search_result_,resource)
                    if len(resource_quark.file_list)>0:

                        await self.save_to_cloud(resource_quark,resource)
                    else:
                        utils.logger.info(f'{title} | {resource_quark.url}无可更新的内容')

                    try:
                        if await self.is_next_need_update(resource.total_episodes,resource.cloud_storage_path):
                            need_update=False
                        else:
                            need_update=True


                    except Exception as e:
                        utils.logger.error(f'{title}|判断网盘是否完全同步全网资源失败{e}')
                        need_update=True

                    cloud_disk_async_info.update({
                        'last_async_time':datetime.now().isoformat(),
                        'need_update':need_update,
                    })
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
    crawler=TMeUCQuarkCrawler()
    sync_cloud=SyncCloudDisk(quark_disk,aria2,alistapi,crawler)
    await sync_cloud.start_async()
    await quark_disk.close()
    await aria2.close()
    await alistapi.close()
    await crawler.close()
    await QuarkShareDirTree.close()

if __name__ == '__main__':
    asyncio.run(main())


