import asyncio
import logging
from typing import List, AsyncGenerator, Tuple

from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import Movie, CloudShareLink
from app.database.movie_repository import movie_repository
from app.modules.filter.interfaces.target_episode_filter_interface import ITargetEpisodeFilter
from app.modules.filter.schemas import TargetEpisode
from app.modules.link_parse.schemas import LinkParse, PrepareParseLinks, ShareFile
from app.utils.async_iterator import AsyncCachedIterator
# 确保从您的新 schemas 文件中导入
from app.modules.data_standard.schemas import StandardizedResult, ResourceType
from app.utils.lazy_load import lazy

logger = logging.getLogger(__name__)


class TargetEpisodeFilter(ITargetEpisodeFilter):

    async def _flatten_file_tree(self, node: ShareFile,target_season_number:int) :
        """
        异步生成器，用于递归地“压平”文件树，返回所有文件节点。
        """
        # 如果是文件，直接 yield
        if not getattr(node, "is_folder", False):
            yield node
            return

        # 如果是文件夹，遍历其子项
        children = await node.children if hasattr(node, "children") else []
        if not children:
            return
        #子项中如果
        children_r=[]
        folder_counts=len([i for i in children if i.is_folder])
        for i in children:
            s=await i.standardized
            if not s.is_folder:
                children_r.append(i)
            else:
                if folder_counts>1:

                    if ResourceType.FOLDER_SEASON in  s.folder_resource_type:
                        if  s.season_number==target_season_number:
                            children_r.append(i)
                    elif ResourceType.FOLDER_RANGE in s.folder_resource_type:
                        children_r.append(i)
                    elif ResourceType.FOLDER_QUALITY in s.folder_resource_type:
                        children_r.append(i)
                else:
                    children_r.append(i)



        for child in children_r:
            if child:
                async for file_node in self._flatten_file_tree(child,target_season_number):
                    yield file_node

    async def _get_target_episode(self, movie: Movie, link_parse: LinkParse) -> TargetEpisode | None:
        """
        使用新的 StandardizedResult 静态方法来寻找目标剧集。
        """
        logger.debug(f"开始从 {link_parse.link.url} 获取目标剧集")
        latest_info = movie.get_latest_episode_info()
        if not latest_info:
            logger.debug(f"[{movie.title}] 无最新剧集信息，跳过")
            return None

        # 步骤 1: 收集所有文件到一个扁平列表
        all_files_nodes = [node async for node in self._flatten_file_tree(link_parse.root,movie.tmdb_infos.season_number)]
        if not all_files_nodes:
            logger.debug("链接中未发现任何文件")
            return None

        # 步骤 2: 并发地获取所有文件的标准化结果
        standardization_tasks = [node.standardized for node in all_files_nodes]
        all_std_results = await asyncio.gather(*standardization_tasks)

        # 将文件节点和其标准化结果配对，并过滤掉无效项
        valid_files_with_std: List[Tuple[ShareFile, StandardizedResult]] = []
        for file_node, std_result in zip(all_files_nodes, all_std_results):
            print(std_result,std_result.resource_type)
            if std_result and (std_result.resource_type in [ResourceType.FILE_EPISODE, ResourceType.FILE_RANGE]):
                valid_files_with_std.append((file_node, std_result))

        if not valid_files_with_std:
            logger.debug("未找到任何有效的剧集或范围文件")
            return None
        #
        # # 步骤 3: 分析需要哪些新剧集
        # # 从所有有效文件中提取出所有可用的集数
        # all_available_eps = StandardizedResult.get_unique_episode_numbers(
        #     [std for _, std in valid_files_with_std]
        # )
        #
        # # 筛选出我们真正需要的新剧集（大于当前最新集）
        # needed_episodes = [ep for ep in all_available_eps if ep > latest]
        #
        # if not needed_episodes:
        #     logger.debug(f"未发现比当前最新集 {latest} 更高的剧集")
        #     return None
        #
        # logger.info(f"发现新剧集: {needed_episodes}")
        #
        # # 步骤 4: 使用 find_optimal_coverage 做出最优决策
        # available_std_results = [std for _, std in valid_files_with_std]
        # optimal_std_selection = StandardizedResult.find_optimal_coverage(
        #     results=available_std_results,
        #     required_episodes=needed_episodes
        # )
        #
        # if not optimal_std_selection:
        #     logger.debug("最优选择算法未能找到任何文件来满足需求")
        #     return None

        # 步骤 5: 从最优的标准化结果反向找到原始的文件节点
        # 创建一个从标准化结果ID到文件节点的映射，以便快速查找
        # std_to_file_map = {id(std): file for file, std in valid_files_with_std}

        # optimal_files = [std_to_file_map[id(std)] for std in optimal_std_selection]
        result_files=[]
        for file_node, std_result in valid_files_with_std:
            result_files.append(file_node)

        logger.info(f"最终选择 {len(result_files)} 个文件来覆盖新剧集: {[f.name for f in result_files]}")
        return TargetEpisode(share_files=result_files, link_parse=link_parse)

    async def get_target_episode(self, movie: Movie, link_parses: AsyncCachedIterator[LinkParse]):
        """
        (此方法保持不变)
        遍历所有解析链接，并为每个链接调用处理逻辑。
        """
        async for lp in link_parses:
            logger.info(f'开始处理链接：--- {lp.link.title} {lp.link.url}')
            try:
                res = await self._get_target_episode(movie, lp)
                if res:
                    logger.info(f'获取到目标剧集组合，来自链接：{res.link_parse.link.url}')
                    yield res
            except Exception as e:
                logger.exception(f"处理链接 {lp.link.url} 时发生错误: {e}")


# ... 后续的 target_episode_filter 和 demo 函数保持不变 ...

target_episode_filter = TargetEpisodeFilter()


async def demo():
    from app.flow.sync_new_movie_flow import link_scraping, link_parse

    await init_db()
    setup_logging()

    movie = await movie_repository.find_by_douban_id('36700700')  # 请确保这个 movie 存在且有 episode_info
    if not movie:
        print("数据库中未找到指定ID的电影，请检查")
        return

    scrape_results = await link_scraping([movie], count=10)
    # 确保 link_parse 的输入格式正确
    prepare_list = [PrepareParseLinks(scrape_quark_links=lazy(lambda: AsyncCachedIterator([])),
        scrape_baidu_links=lazy(lambda: AsyncCachedIterator([])),links=[CloudShareLink(url='https://pan.baidu.com/s/1hnK7pBNEjSKMjEYGlAYfRw?pwd=1016')], movie=s.movie) for s in scrape_results]
    parses_results = await link_parse(prepare_list)
    # for r in parses_results:
    #     async for i in r.baidu_parses:
    #         for j in await i.root.children:
    #             for k in await j.children:
    #                 print((await k.standardized))
    # get_target_episode 现在是异步生成器，需要用 async for 消费
    async for episode_filter_result in target_episode_filter.get_target_episode(movie, parses_results[0].baidu_parses):
        print(f"找到一个最优剧集组合，包含 {len(episode_filter_result.share_files)} 个文件。")
        for f in episode_filter_result.share_files:
            print(f"  - {f.name}")


if __name__ == '__main__':
    asyncio.run(demo())