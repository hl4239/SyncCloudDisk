import asyncio
import copy
import json
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import Optional

from agents import function_tool, Runner
from google import genai
from google.genai import types, client
from pydantic import BaseModel,Field
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

import settings
import utils
from QuarkDisk import QuarkDisk
from Services.quark_share_dir_tree import QuarkShareDirTree
from database import engine
from models.resource import Resource, ResourceCategory
from pansearch.providers import AipansouProvider
from utils import get_ai_agent


class AsyncCloudDisk:

    class OutPutLatestEpisodeFile(BaseModel):

        absolute_path:str

    class OutPutEpisodeFile(BaseModel):
        desc_absolute_path_list:list[str]=Field(description="按照剧集信息的降序排序的绝对路径文件名")
        share_link_file_correspond_my_cloud:str=Field(description='与{my_cloud_disk_updated_file_name}剧集相对应的绝对路径文件名,如果{my_cloud_disk_updated_file_name}=""或者找不到对应文件时，就返回""即为空字符串')
        is_share_link_synchronized:bool=Field(description='网盘分享链接的剧集是否已与影视数据库同步')
        # is_my_cloud_disk_newer:bool=Field(description='当{my_cloud_disk_updated_file_name}!=""同时比{share_link_updated_file_name}的剧集信息newer时，则为true,否则false')

    output_latest_file:OutPutLatestEpisodeFile
    _output_need_update_files:Optional[OutPutEpisodeFile]=None
    @staticmethod
    @function_tool
    async def parse_share_link(share_link:str,max_deep:int=1):
        """
        解析分享链接

        :param max_deep: 遍历深度，默认为1
        :param share_link:分享链接
        :return:目录树
        """
        print("parse_share_link")

        quark_share_tree= QuarkShareDirTree.get_quark_share_tree(share_link)
        await  quark_share_tree .parse(max_deep=max_deep)
        result=quark_share_tree.ls_dir()
        print(result)
        return result
    @staticmethod
    @function_tool
    async def output_latest_episode_file(latest_episode_file: OutPutLatestEpisodeFile):
        """
        输出最新剧集文件
        :param latest_episode_file: 最终剧集信息的类对象
        :return: 无返回值，默认视为成功
        """
        AsyncCloudDisk.output_latest_episode_file=latest_episode_file
    @staticmethod
    @function_tool
    async def output_need_update_episode_file(episode_file_list: OutPutEpisodeFile):
        """
        输出需要更新的文件
        :param episode_file_list: 需要更新的文件的集合
        :return: 无返回值，默认视为成功
        """
        AsyncCloudDisk._output_need_update_files = episode_file_list
    @staticmethod
    async def get_last_output_need_update_files():
        if AsyncCloudDisk._output_need_update_files is not None:
            result=  copy.deepcopy(AsyncCloudDisk._output_need_update_files)
            AsyncCloudDisk._output_need_update_files=None
        else:
            result=None
        return result
    @staticmethod
    async def get_need_update_file():

        share_link='https://pan.quark.cn/s/56be9bc04175'
        title='无忧渡'
        agent=get_ai_agent('你将根据我提供的影视资源链接分析得出最新剧集的资源文件名，同时输出该文件名的绝对路径,例如：你在”/目录/子目录/“的目录下找到最新的剧集文件名:”20.mkv“，并调用工具{output_latest_episode_file}输出最新剧集文件：”/目录/子目录/20.mkv“。我将提供以下参数：'
                         '1.{share_link}代表资源链接 '
                         '2.{title}代表影视资源title。'
                         '收到参数后,无需与我交互，你能根据以下不同的情况做出决策：'
                         '1.当面临多个文件夹选择时，如果每个文件夹代表不同版本的影视资源时，你需要根据{title}参数判断选择目录。例如：{title}=“飞驰人生2”，文件夹1代表第一季，文件夹2代表第二季，你将选择文件夹2'
                         '2.当面临多个文件夹选择时，如果每个文件夹代表影视资源的清晰度时，你需要选择清晰度最高的文件夹。例如文件夹1代表1080p，文件夹2代表4k，你需要选择文件夹2'
                         '3.当面临多个文件夹选择时，如果文件夹代表一个合集时，你只需要关注最新剧集所在的文件夹。例如：文件夹1代表1-10集，文件夹2代表11-20集，即你应该关注文件夹2'
                         '4.当面临.mkv .mp4  文件夹共存在同一个目录下时，优先分析.mkv .mp4文件名并得到最新剧集信息'
                         '5.只关注后缀名为.mp4 .mkv的文件',tools=[AsyncCloudDisk.parse_share_link,AsyncCloudDisk.output_latest_episode_file])

        result=    await  Runner.run(agent, input=f'{{share_link}}="{share_link}" {{title}}="{title}"')
        output=AsyncCloudDisk.output_latest_episode_file
        if output is not None:
            print(f'结构化输出：{output.absolute_path}')
        else:
            print(f'结构化输出失败')
    @staticmethod
    async def get_need_update_file_1(share_link:str,title:str,updated_file_name:str,total_episodes:str):
        """
        通过ai对所有文件名降序排序，然后根据网盘已经更新的文件，截取list在已更新文件之后的文件list
        :return:
        """
        prompt = """
        **Objective**: Synchronize my cloud disk with the latest episodes of a TV show/movie by comparing shared resource links and online metadata.

        ### **Input Parameters**:
        1. **`{share_link}`**: A shared cloud storage link containing video resources (`.mp4`/`.mkv` files).
        2. **`{title}`**: The title of the media (e.g., "Movie Name S02").
        3. **`{my_cloud_disk_updated_file_name}`**: The filename of the latest episode in my cloud disk. If `""`, my disk is empty/unsynced.
        4. **`{Internet_updated_info}`**: Metadata from an online database (e.g., latest episode number/version).

        ### **Workflow Steps**:
        1. **Parse Shared Link**:
           - Use tool `{parse_share_link}` to extract the directory tree from `{share_link}`.
        2. **Validate Resource-Title Match**:
           - Verify that the `{share_link}` content matches `{title}` by:
           - If mismatch → Abort with error "Resource does not match specified title".
        3. **Filter & Sort Files**:
           - **Target files**: Only `.mp4` and `.mkv` files.
           - **Sort**: Descending order by filename → stored as `{desc_absolute_path_list}`.
        4. **Identify Latest Shared File**:
           - Extract the newest file from `{desc_absolute_path_list}` → `{share_link_updated_file_name}`.
           - Compare with `{Internet_updated_info}`:
             - If metadata matches → `{is_share_link_synchronized} = true`.
             - Else → `{is_share_link_synchronized} = false`.
        5. **Locate Corresponding File**:
           - In `{desc_absolute_path_list}`, find the file matching `{my_cloud_disk_updated_file_name}` → `{share_link_file_correspond_my_cloud}`.
        6. **Output Result**:
           - Use tool `{output_need_update_episode_file}` to generate the sync plan.
        ### **Directory Traversal Rules**:
        1. **Multiple Folders (Different Versions)**:
           - Choose the folder matching `{title}` (e.g., for `{title}="Movie S02"`, ignore "Movie S01").
        2. **Multiple Folders (Resolutions)**:
           - Select the highest resolution (e.g., 4K > 1080p).
        3. **Multiple Folders (Episode Bundles)**:
           - If folders split episodes (e.g., "1-10", "11-20") and `{my_cloud_disk_updated_file_name}` is in a later range (e.g., "11.mkv"), ignore earlier folders.
        ### **Notes**:
        - **Autonomous Execution**: Proceed without interactive confirmation unless critical ambiguity arises.
        - **Priority**: Ensure `{share_link_updated_file_name}` aligns with `{Internet_updated_info}` for accurate sync.
        """
        agent = get_ai_agent(
            prompt
            ,
            tools=[AsyncCloudDisk.parse_share_link, AsyncCloudDisk.output_need_update_episode_file])

        result = await  Runner.run(agent, input=f'{{share_link}}="{share_link}" {{title}}="{title}" {{my_cloud_disk_updated_file_name}}="{updated_file_name}" {{Internet_updated_info}}="{total_episodes}"')
        print(f"final-output: {result.final_output}")
        output =await AsyncCloudDisk.get_last_output_need_update_files()

        return output




    @staticmethod
    async def start_async(quark_disk:QuarkDisk):

        with Session(engine) as session:
            statement = select(Resource).where(Resource.category == ResourceCategory.HOT_CN_DRAMA).order_by(
                Resource.douban_last_async.desc()).limit(settings.select_resource_num)
            results = session.exec(statement)
            resources = results.all()
            # resources=[resource for resource in resources if resource.title=='狮城山海(2025)']
            for resource in resources:
                douban_episode_update=resource.douban_last_episode_update
                cloud_disk_async_info=resource.cloud_disk_async_info
                if cloud_disk_async_info is None:
                    cloud_disk_async_info={}
                cloud_disk_async_time = datetime.fromisoformat(cloud_disk_async_info['last_async_time']) if cloud_disk_async_info.get('last_async_time') else None

                is_skip_update=cloud_disk_async_info.get('is_skip_update',False)
                is_force_update=cloud_disk_async_info.get('is_force_update',False)
                if (((cloud_disk_async_time is None) or (cloud_disk_async_time < douban_episode_update)) and is_skip_update==False)or is_force_update:
                    title=resource.title
                    total_episodes=resource.total_episodes
                    aipansou_provider = AipansouProvider()
                    last_share_link=cloud_disk_async_info.get('share_link',None)
                    last_share_link_list=[]
                    if last_share_link is not None:
                        last_share_link_list.append(last_share_link)
                    update_share_link_combined_iter = chain(last_share_link_list,cloud_disk_async_info.get('update_share_link_list',[]), aipansou_provider.search(title,num=5))
                    for result in update_share_link_combined_iter:
                        if isinstance(result, str):
                            share_link=result
                        else:
                            share_link = result.url
                        cloud_disk_updated_episode_file=cloud_disk_async_info.get('updated_episode_file')
                        output=    await  AsyncCloudDisk.get_need_update_file_1(share_link,title,cloud_disk_updated_episode_file,total_episodes)
                        need_update_absolute_files = []

                        if output is not None:
                            print(
                                f'结构化输出：{output.desc_absolute_path_list} | {output.share_link_file_correspond_my_cloud} | {output.is_share_link_synchronized}')
                            if output.is_share_link_synchronized:
                                if output.share_link_file_correspond_my_cloud == "":

                                    need_update_absolute_files = output.desc_absolute_path_list
                                else:
                                    for episode_file in output.desc_absolute_path_list:
                                        if episode_file == output.share_link_file_correspond_my_cloud:
                                            break
                                        else:
                                            need_update_absolute_files.append(episode_file)
                                if len(need_update_absolute_files) > 0:
                                    quark_share_tree = QuarkShareDirTree.get_quark_share_tree(share_link)
                                    node_info_list = []
                                    for f in need_update_absolute_files:
                                        node = quark_share_tree.get_node_info(f)
                                        node_info_list.append(node)

                                    print(json.dumps(node_info_list, indent=4, ensure_ascii=False))

                                    if None in node_info_list:
                                        error = cloud_disk_async_info.get('error', [])
                                        error.append(f'ai返回需要更新的文件list 存在错误:{node_info_list}')
                                        cloud_disk_async_info.update({
                                            'error': error
                                        })
                                        utils.logger.warning(f'{title}|{share_link}⚠ai返回需要更新的文件list 存在错误:{node_info_list}')

                                    node_info_list = [i for i in node_info_list if i is not None]
                                    pwd_id = quark_share_tree.ParseQuarkShareLInk.pwd_id
                                    stoken = quark_share_tree.ParseQuarkShareLInk.stoken
                                    fid_list = [i['fid'] for i in node_info_list]
                                    share_fid_token_list = [i['share_fid_token'] for i in node_info_list]
                                    to_pdir_path = resource.cloud_storage_path
                                    try:
                                        await  quark_disk.mkdir(to_pdir_path)
                                        utils.logger.info(f"{title}|{share_link}创建{to_pdir_path}成功")
                                    except Exception as e:
                                        utils.logger.error(f'{title}|{share_link}❌创建网盘目录失败 {str(e)}')
                                    to_pdir_fid = (await quark_disk.get_fids([to_pdir_path]))[0]['fid']
                                    try:
                                        if await  quark_disk.save_file(fid_list=fid_list,
                                                                       fid_token_list=share_fid_token_list,
                                                                       to_pdir_fid=to_pdir_fid, stoken=stoken,
                                                                       pwd_id=pwd_id):
                                            utils.logger.info(f'{title}|{share_link}✅转存到{to_pdir_path}成功')
                                            updated_episode_file = node_info_list[0]['file_name']
                                            now = datetime.now()
                                            cloud_disk_async_info.update({
                                                'updated_episode_file': updated_episode_file,
                                                'last_async_time': now.isoformat(),
                                                'error': [],
                                                'share_link': share_link,
                                            })
                                        else:
                                            error = cloud_disk_async_info.get('error', [])
                                            error.append(f'❌转存失败')
                                            cloud_disk_async_info.update({
                                                'error': error
                                            })
                                            utils.logger.error(f'{title}|{share_link}❌转存失败')
                                    except Exception as e:
                                        error = cloud_disk_async_info.get('error', [])
                                        error.append(f'{e}')
                                        cloud_disk_async_info.update({
                                            'error': error
                                        })
                                        utils.logger.error(f'{title}|{share_link}❌转存失败，抛出异常：{str(e)}')
                                    try:
                                        resource.cloud_disk_async_info = cloud_disk_async_info
                                        flag_modified(resource, "cloud_disk_async_info")
                                        session.add(resource)
                                        session.commit()
                                        break
                                    except Exception as e:
                                        utils.logger.error(f'{title}|{share_link}❌数据库保存异常{str(e)}')
                                else:

                                    utils.logger.info(f'{title}|{share_link}:⚠无可更新剧集文件')
                            else:
                                utils.logger.error(f'{title}|{share_link}资源链接不存在与total_episodes相等的文件')
                        else:
                            utils.logger.error(f'{title}|{share_link} ai输出为None')





            





async def main():
    share_link = 'https://pan.quark.cn/s/56be9bc04175'
    title = '无忧渡'
    updated_file_name = ''
    # result=await AsyncCloudDisk.get_need_update_file_1(share_link=share_link,title=title,updated_file_name=updated_file_name)
    quark_disk=QuarkDisk(settings.STORAGE_CONFIG['quark'][0])
    await quark_disk.connect()
    await AsyncCloudDisk.start_async(quark_disk)
    await quark_disk.close()
    await QuarkShareDirTree.close()
if __name__ == '__main__':
    asyncio.run(main())