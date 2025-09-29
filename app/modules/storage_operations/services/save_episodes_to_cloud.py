import asyncio
import logging
from datetime import datetime
from pathlib import Path
from time import timezone
from typing import List

import pytz

from app.database.models import  MovieCloudInfo, CloudShareLink

from app.modules.link_parse.schemas import ShareFile, QuarkLinkParse, PrepareParseLinks, LinkParse
from app.modules.storage_operations.interfaces.cloud_disk_operator_interface import ICloudDiskOperator
from app.modules.storage_operations.interfaces.save_episodes_to_cloud_interface import ISaveEpisodesToCloud
from app.modules.storage_operations.services.quark_cloud_operator import QuarkCloudOperator


logger=logging.getLogger(__name__)
class SaveEpisodesToCloud(ISaveEpisodesToCloud):
    async def save_to_cloud(
            self,
            share_files: List[ShareFile],
            parse: LinkParse,
            cloud_info: MovieCloudInfo,
            base_path: Path,
            operator: ICloudDiskOperator
    ):
        global share_link
        base_path_ = base_path / cloud_info.pdir_name
        result = False

        pdir_file = await operator.ensure_get_dir(base_path_)
        ls_dir_result = await operator.ls_dir(pdir_file=pdir_file)
        exited_cloud_episode_files = await self.pancloud_episode_filter(pdir_file=pdir_file)
        exited_episode_number = [
            (await i.standardized).episode_number for i in exited_cloud_episode_files
        ]

        to_save_share_files = []
        added_episodes_numbers = []
        for share_file in share_files:
            st = await share_file.standardized
            if st.episode_number:
                if (
                        st.episode_number not in exited_episode_number
                        and st.episode_number not in added_episodes_numbers
                ):
                    to_save_share_files.append(share_file)
                    added_episodes_numbers.append(st.episode_number)

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

        # 更新 cloud_info
        latest_episode_number = max(
            [(await i.standardized).episode_number for i in await pdir_file.children]) if await pdir_file.children else None
        share_link=None

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
                    new_name = (await to_save_share_file_maps[i.name].standardized).standardized_episode_name
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
    from app.modules.link_parse.services.quark_link_parser import quark_link_parser

    await init_db()
    setup_logging()
    # quark = QuarkCloudOperator("4295quark")
    # r= await quark.ls_dir(Path('/资源分享/TvCategory.HOT_CN_DRAMA/2025/护宝寻踪'))
    #
    # for i in r:
    #     print(i.name,(await i.standardized).episode_number)
    # r= await quark.mkdir(Path('/这是新目录'))
    movie = await movie_repository.find_by_douban_id('36455616')

    result = await quark_link_parser.parse_links([PrepareParseLinks(
        links=[CloudShareLink(url='https://pan.quark.cn/s/969ddab7b51e', title='赴山海')],
        scrape_quark_links=lazy(lambda: AsyncCachedIterator([])), movie=movie)])

if __name__ == '__main__':
    asyncio.run(main())






