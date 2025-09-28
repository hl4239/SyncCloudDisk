import logging
from typing import List

from app.database.models import Movie
from app.modules.filter.schemas import TargetEpisodeFilterResult, TargetEpisode
from app.modules.filter.services.regex_target_link_filter import regex_target_link_filter
from app.modules.filter.services.target_episode_filter_service import target_episode_filter
from app.modules.link_parse.schemas import LinkParseResult
from app.utils.async_iterator import AsyncCachedIterator

logger=logging.getLogger(__name__)
async def title_and_episode_filter_flow(link_parse_results:List[LinkParseResult])->List[TargetEpisodeFilterResult]:
    filter_1_result=await regex_target_link_filter.filter(link_parse_results)
    # filter_2_result=await only_one_movie_filter(filter_1_result)
    filter_2_result=await target_episode_filter.filter(filter_1_result)
    return filter_2_result

async def full_episode_filter_flow(link_parse_results:List[TargetEpisodeFilterResult]):
    async def f1(target:AsyncCachedIterator[TargetEpisode],m:Movie):
        async for r1 in target:
            max_share_file_episode_number=max([(await i.standardized).episode_number for i in r1.share_files])
            latest_episode_number=m.get_latest_episode_info().episode_number
            if max_share_file_episode_number>=latest_episode_number:
                logger.info(f'{m.title_season} | {r1.link_parse.link.url}选择该分享链接，已更新到最新剧集{max_share_file_episode_number}')
                yield r1
            else:
                logger.info(f'{m.title_season} | {r1.link_parse.link.url}跳过，因为最新剧集={latest_episode_number} 而分享链接只更新到{max_share_file_episode_number}')



    for r in link_parse_results:
        r.quark_result=AsyncCachedIterator(f1(r.quark_result,r.movie))
    return link_parse_results
