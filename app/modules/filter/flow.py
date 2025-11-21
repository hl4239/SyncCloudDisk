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
    return filter_3_result



async def full_episode_filter_flow(
    link_parse_results: List[TargetEpisodeFilterResult],
    is_skip_not_latest: bool = False,
    skip_target_season: bool = True,
    tolerance: int = 2
) -> List[TargetEpisodeFilterResult]:
    """
    完整分集筛选流程（主入口）
    说明：
      - 该函数不会改变原有业务逻辑，只会将每个结果的 quark_result / baidu_result
        包装为新的 AsyncCachedIterator（内部使用 f1 协程生成器）。
      - 日志级别约定：
          * logger.debug：记录详细内部状态（用于开发/调试）
          * logger.info：记录关键业务决策（选择/备选/跳过/遍历完成）
          * logger.warning：记录异常或需要关注的情况（如更新超出容忍范围）
    参数：
      - link_parse_results: 输入的解析结果列表，每项包含 movie、quark_result、baidu_result 等
      - is_skip_not_latest: 是否跳过非最新（若为 True，则不会在没有最新的情况下返回备选）
      - skip_target_season: 是否仅保留目标季的 share_files（按 movie.get_season_number() 过滤）
      - tolerance: 允许超前最新集数的容忍值（超过 latest + tolerance 会发 warning，但不改变逻辑）
    返回：
      - 修改后的 link_parse_results（每个 r.quark_result / r.baidu_result 被替换为 AsyncCachedIterator）
    """

    logger.debug(
        "full_episode_filter_flow called "
        f"len(link_parse_results)={len(link_parse_results)} is_skip_not_latest={is_skip_not_latest} "
        f"skip_target_season={skip_target_season} tolerance={tolerance}"
    )

    async def f1(target: AsyncCachedIterator[TargetEpisode], m: Movie):
        """
        对单个 movie 的单个来源（如 quark/baidu）进行遍历筛选的内部生成器。
        逻辑（与原代码保持一致）：
          - 遍历 target（异步迭代每个解析到的分享结果 r1）
          - 若 skip_target_season 为 True，则先按季号过滤 r1.share_files
          - 计算该分享链接能覆盖到的最大剧集号 max_share_file_episode_number
          - 若 max_share_file_episode_number >= latest_episode_number：
              -> 若超出 latest + tolerance 则记录 warning（不改变逻辑）
              -> 记录 info 并 yield r1（立即返回该链接，认为为“最新”）
          - 否则：
              -> 维护一个 more_episodes_f 作为当前“最佳备选”（最大 episode_number）
              -> 记录 info（作为备选或跳过）
        遍历结束后：
          - 若存在备选且 is_skip_not_latest 为 False，则 yield 该备选（返回备选）
          - 记录遍历完成的 info（无可用链接）
        """
        logger.debug(f"f1 start for movie: {m.title_season}")

        # 保存当前发现的“最佳备选”：(r1, max_share_file_episode_number)
        more_episodes_f = None

        # 目标视频的最新剧集号（由 Movie 提供）
        latest_episode_number = m.get_latest_episode_info().episode_number
        logger.debug(f"{m.title_season} latest_episode_number={latest_episode_number}")

        async for r1 in target:
            # 进入每个候选分享链接的处理
            logger.debug(f"Processing candidate link: {r1.link_parse.link.url}")

            if skip_target_season:
                # 若只保留目标季的文件，则根据 movie 的季号过滤 share_files 列表
                season_number = m.get_season_number()
                logger.debug(
                    f"{m.title_season} apply skip_target_season filter: season_number={season_number} "
                    f"before_count={len(r1.share_files)}"
                )
                # 保持原始逻辑：按 season 过滤 share_files（注意 await i.standardized）
                r1.share_files = [
                    i for i in r1.share_files if (await i.standardized).season_number == season_number
                ]
                logger.debug(f"{m.title_season} after season filter count={len(r1.share_files)}")

            # 计算该分享链接包含的所有标准化后的剧集号集合
            standardized_list = [await i.standardized for i in r1.share_files]
            episode_numbers = StandardizedResult.get_unique_episode_numbers(standardized_list)
            logger.debug(f"{m.title_season} | {r1.link_parse.link.url} episode_numbers={episode_numbers}")

            # 取该分享链接能覆盖到的最大剧集号（无文件时为 -1）
            max_share_file_episode_number = max(episode_numbers, default=-1)
            logger.debug(
                f"{m.title_season} | {r1.link_parse.link.url} "
                f"max_share_file_episode_number={max_share_file_episode_number}"
            )

            if max_share_file_episode_number >= latest_episode_number:
                # 若达到或超过最新集，则视为“最新”，直接选择并返回该链接
                # 若超过 tolerance，记录 warning（但不阻止选择）
                if max_share_file_episode_number > latest_episode_number + tolerance:
                    logger.warning(
                        f'{m.title_season} | {r1.link_parse.link.url} 更新超出容忍范围,被跳过: '
                        f'{max_share_file_episode_number} > {latest_episode_number} + {tolerance}'
                    )
                    continue

                logger.info(
                    f'{m.title_season} | {r1.link_parse.link.url} 已更新到最新剧集 '
                    f'{max_share_file_episode_number}，选择该分享链接'
                )
                logger.debug(f"{m.title_season} yielding latest candidate: {r1.link_parse.link.url}")
                yield r1  # ✅ 找到最新的，直接返回

            else:
                # 否则将其作为备选或跳过（根据是否比当前备选更优）
                if not more_episodes_f or max_share_file_episode_number > more_episodes_f[1]:
                    # 更新当前的“最佳备选”
                    more_episodes_f = (r1, max_share_file_episode_number)
                    logger.info(
                        f'{m.title_season} | {r1.link_parse.link.url} 作为备选（更新至 '
                        f'{max_share_file_episode_number}/{latest_episode_number}）'
                    )
                    logger.debug(
                        f"{m.title_season} updated more_episodes_f to "
                        f"{r1.link_parse.link.url} | {max_share_file_episode_number}"
                    )
                else:
                    # 当前候选比已有备选更差，跳过
                    logger.info(
                        f'{m.title_season} | {r1.link_parse.link.url} 跳过（更新至 '
                        f'{max_share_file_episode_number}，比备选'
                        f'{more_episodes_f[0].link_parse.link.url} | {more_episodes_f[1]} 更少）'
                    )
                    logger.debug(
                        f"{m.title_season} skipped candidate {r1.link_parse.link.url}: "
                        f"{max_share_file_episode_number} <= {more_episodes_f[1]}"
                    )

        # 遍历结束：如有备选且允许返回非最新（is_skip_not_latest=False），则返回该备选
        if more_episodes_f and not is_skip_not_latest:
            logger.info(
                f'{m.title_season} 遍历完成，最终选择 {more_episodes_f[0].link_parse.link.url} '
                f'更新至 {more_episodes_f[1]} 作为目标分享链接'
            )
            logger.debug(f"{m.title_season} yielding backup candidate: {more_episodes_f[0].link_parse.link.url}")
            yield more_episodes_f[0]  # ✅ 返回一致的类型

        # 无论是否有备选，都记录遍历完成（便于上层跟踪）
        logger.info(f'{m.title_season}分享链接遍历完成，无可用分享链接')
        logger.debug(f"f1 end for movie: {m.title_season}")

    # 将每个解析结果的来源包装为 AsyncCachedIterator（保持原始行为）
    for r in link_parse_results:
        logger.debug(f"Wrapping quark_result and baidu_result for: {r.movie.title_season}")
        r.quark_result = AsyncCachedIterator(f1(r.quark_result, r.movie))
        r.baidu_result = AsyncCachedIterator(f1(r.baidu_result, r.movie))

    logger.debug("full_episode_filter_flow complete, returning modified link_parse_results")
    return link_parse_results

