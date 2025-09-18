from typing import List

from app.modules.filter.schemas import TargetEpisodeFilterResult
from app.modules.filter.services.only_one_movie_filter import only_one_movie_filter
from app.modules.filter.services.regex_target_link_filter import regex_target_link_filter
from app.modules.filter.services.target_episode_filter_service import target_episode_filter
from app.modules.link_parse.schemas import LinkParseResult


async def filter_flow(link_parse_results:List[LinkParseResult])->List[TargetEpisodeFilterResult]:
    filter_1_result=await regex_target_link_filter.filter(link_parse_results)
    # filter_2_result=await only_one_movie_filter(filter_1_result)
    filter_2_result=await target_episode_filter.filter(filter_1_result)
    return filter_2_result