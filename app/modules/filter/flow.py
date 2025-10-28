import logging
from typing import List

from app.database.models import Movie
from app.modules.data_standard.schemas import StandardizedResult
from app.modules.filter.schemas import TargetEpisodeFilterResult, TargetEpisode
from app.modules.filter.services.regex_target_link_filter import regex_target_link_filter
from app.modules.filter.services.target_episode_filter_service import target_episode_filter
from app.modules.link_parse.schemas import LinkParseResult
from app.utils.async_iterator import AsyncCachedIterator

logger=logging.getLogger(__name__)
async def title_and_episode_filter_flow(link_parse_results:List[LinkParseResult],is_skip_not_latest)->List[TargetEpisodeFilterResult]:
    filter_1_result=await regex_target_link_filter.filter(link_parse_results)
    filter_2_result=await target_episode_filter.filter(filter_1_result)
    filter_3_result=await full_episode_filter_flow(filter_2_result,is_skip_not_latest)
    return filter_2_result

async def full_episode_filter_flow(link_parse_results:List[TargetEpisodeFilterResult],is_skip_not_latest:bool=False)->List[TargetEpisodeFilterResult]:
    async def f1(target: AsyncCachedIterator[TargetEpisode], m: Movie):
        more_episodes_f = None
        latest_episode_number = m.get_latest_episode_info().episode_number

        async for r1 in target:
            episode_numbers = StandardizedResult.get_unique_episode_numbers([await i.standardized for i in r1.share_files])
            max_share_file_episode_number = max(episode_numbers, default=-1)

            if max_share_file_episode_number >= latest_episode_number:
                logger.info(
                    f'{m.title_season} | {r1.link_parse.link.url} 已更新到最新剧集 {max_share_file_episode_number}，选择该分享链接')
                yield r1  # ✅ 找到最新的，直接返回
            else:
                if not more_episodes_f or max_share_file_episode_number > more_episodes_f[1]:
                    more_episodes_f = (r1, max_share_file_episode_number)
                    logger.info(
                        f'{m.title_season} | {r1.link_parse.link.url} 作为备选（更新至 {max_share_file_episode_number}/{latest_episode_number}）')
                else:
                    logger.info(
                        f'{m.title_season} | {r1.link_parse.link.url} 跳过（更新至 {max_share_file_episode_number}，比备选{more_episodes_f[0].link_parse.link.url} | {more_episodes_f[1]} 更少）')

        if more_episodes_f and not is_skip_not_latest:
            logger.info(
                f'{m.title_season} 遍历完成，最终选择 {more_episodes_f[0].link_parse.link.url} 更新至 {more_episodes_f[1]} 作为目标分享链接')
            yield more_episodes_f[0]  # ✅ 返回一致的类型
        logger.info(
            f'{m.title_season}分享链接遍历完成，无可用分享链接')

    for r in link_parse_results:
        r.quark_result=AsyncCachedIterator(f1(r.quark_result,r.movie))
        r.baidu_result=AsyncCachedIterator(f1(r.baidu_result,r.movie))
    return link_parse_results

