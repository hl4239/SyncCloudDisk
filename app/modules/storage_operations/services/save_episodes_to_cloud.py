import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List

import pytz

from app.database.models import  MovieCloudInfo, CloudShareLink
from app.modules.data_standard.schemas import StandardizedResult
from app.modules.filter.schemas import TargetEpisode

from app.modules.link_parse.schemas import ShareFile,  PrepareParseLinks, LinkParse
from app.modules.storage_operations.interfaces.cloud_disk_operator_interface import ICloudDiskOperator
from app.modules.storage_operations.interfaces.save_episodes_to_cloud_interface import ISaveEpisodesToCloud
from app.utils.async_iterator import AsyncCachedIterator

logger=logging.getLogger(__name__)
class SaveEpisodesToCloud(ISaveEpisodesToCloud):
    async def save_to_cloud(
            self,target_episode_files: AsyncCachedIterator[TargetEpisode],

            cloud_info: MovieCloudInfo,
            operator: ICloudDiskOperator
    ):
        """
        并不严格根据cloud_info.save_suffixes保存，因为可能导致最新集数补全，所以，只要确保含有save_suffixes中的后缀，
        然后根据save_suffixes作为最高优先级去选择，
        :param target_episode_files:
        :param cloud_info:
        :param operator:
        :return:
        """
        global share_link
        target_episode_parse_=None
        async for target_episode_parse in target_episode_files:

            target_suffiexes = [i for i in target_episode_parse.share_files if (await i.standardized).suffix in cloud_info.save_suffixes]
            if len(target_suffiexes)>0:
                target_episode_parse_=target_episode_parse
                break
        if not target_episode_parse_:
            logger.info(f'未筛选到适合{cloud_info.save_suffixes}的链接')
            return

        share_files=target_episode_parse_.share_files
        parse=target_episode_parse_.link_parse


        base_path_ = Path(cloud_info.cloud_path)
        result = False

        pdir_file = await operator.ensure_get_dir(base_path_)
        ls_dir_result = await operator.ls_dir(pdir_file=pdir_file)
        exited_cloud_episode_files = await self.pancloud_episode_filter(pdir_file=pdir_file)
        cloud_standards=[await i.standardized for i in exited_cloud_episode_files]


        share_standards=[await i.standardized for i in share_files]

        cloud_episode_numbers =StandardizedResult.get_unique_episode_numbers(cloud_standards)
        share_episode_numbers=StandardizedResult.get_unique_episode_numbers(share_standards)
        need_episode_numbers = set(share_episode_numbers) - set(cloud_episode_numbers)
        latest_episode_number= max(max(cloud_episode_numbers or [-1]), max(share_episode_numbers or [-1]))
        need_standards=StandardizedResult.find_optimal_coverage(share_standards,list(need_episode_numbers))
        to_save_share_files=[]
        for i in share_files:
            s=await i.standardized
            for j in need_standards:
                if s is j:
                    to_save_share_files.append(i)



        logger.info(f" Saving {len(to_save_share_files)} episodes to {cloud_info.pancloud_name} {base_path_}")
        try:
            await operator.save_file(share_files=to_save_share_files, parse=parse, pdir_file=pdir_file,ensure_shared_file_exist=True,wait_timeout=10,poll_interval=1)
            result = True
            logger.info(f"✅ Saved {len(to_save_share_files)} episodes to {cloud_info.pancloud_name} {base_path_}")
        except Exception as e:
            logger.error(
                f"❌ Save error {len(to_save_share_files)} episodes to {cloud_info.pancloud_name} {base_path_} : {e}")

        # 异步后台重命名任务
        asyncio.create_task(
            self._rename_files_background(to_save_share_files, operator, pdir_file)
        )




        cloud_info.last_save_link = parse.link.url
        cloud_info.last_save_time = datetime.now(pytz.timezone("Asia/Shanghai"))
        cloud_info.last_save_success = result

        cloud_info.latest_episode_number = latest_episode_number
        if not cloud_info.share_link and cloud_info.last_save_success:
            cloud_info.share_link=await operator.create_share_link(files=[pdir_file])
    async def _rename_files_background(
            self,
            to_save_share_files: List[ShareFile],
            operator: ICloudDiskOperator,
            pdir_file
    ):
        """后台执行的重命名任务"""
        try:
            ls_files = await operator.ls_dir(pdir_file=pdir_file)
            to_save_share_file_maps = {i.name: i for i in to_save_share_files}

            for i in ls_files:
                if i.name in to_save_share_file_maps.keys():
                    new_name = (await to_save_share_file_maps[i.name].standardized).standardized_name
                    try:
                        if await operator.rename(i, new_name):
                            logger.info(f'✅成功重命名 {i.name} -> {new_name}')
                    except Exception as e:
                        logger.error(f'❌失败重命名 {i.name} -> {new_name} ：{e}')
                    await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"❌ 后台重命名任务失败: {e}")


save_episodes_to_cloud_service=SaveEpisodesToCloud()

async def main():
    from app.core.logging_config import setup_logging
    from app.database.database import init_db
    from app.database.movie_repository import movie_repository
    from app.utils.async_iterator import AsyncCachedIterator
    from app.utils.lazy_load import lazy
    from app.modules.link_parse.services.link_parser import link_parser

    await init_db()
    setup_logging()
    # quark = QuarkCloudOperator("4295quark")
    # r= await quark.ls_dir(Path('/资源分享/TvCategory.HOT_CN_DRAMA/2025/护宝寻踪'))
    #
    # for i in r:
    #     print(i.name,(await i.standardized).episode_number)
    # r= await quark.mkdir(Path('/这是新目录'))
    movie = await movie_repository.find_by_douban_id('36455616')

    result = await link_parser.parse_links([PrepareParseLinks(
        links=[CloudShareLink(url='https://pan.quark.cn/s/969ddab7b51e', title='赴山海')],
        scrape_quark_links=lazy(lambda: AsyncCachedIterator([])), movie=movie)])

if __name__ == '__main__':
    asyncio.run(main())






