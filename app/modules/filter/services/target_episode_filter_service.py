import asyncio
import logging

from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import Movie
from app.database.movie_repository import movie_repository
from app.modules.filter.interfaces.target_episode_filter_interface import ITargetEpisodeFilter
from app.modules.filter.schemas import TargetEpisode
from app.modules.link_parse.schemas import LinkParse, PrepareParseLinks
from app.utils.async_iterator import AsyncCachedIterator
from app.modules.data_standard.schemas import  ResourceType
from app.utils.lazy_load import lazy

logger = logging.getLogger(__name__)


class TargetEpisodeFilter(ITargetEpisodeFilter):
    _QUALITY_RANK = {
        "2160p": 7, "4k": 7, "8k": 8,
        "1080p": 6, "fhd": 6, "hd": 5,
        "720p": 5, "480p": 3,
        "web-dl": 5, "webrip": 5, "bluray": 6, "bdrip": 6,
        "remux": 7, "uhd": 7, "hdr": 6
    }

    def _quality_rank(self, q):
        if not q:
            return 0
        k = q.lower().replace("-", "").replace("_", "").replace(" ", "")
        for key, val in self._QUALITY_RANK.items():
            if key.replace("-", "") in k:
                return val
        return 0

    def _guess_quality_from_name(self, name):
        if not name:
            return None
        n = name.lower()
        for key in self._QUALITY_RANK:
            if key in n:
                return key.upper()
        return None

    async def _get_target_episode(self, movie: Movie, link_parse: LinkParse):
        logger.debug(f"开始从{link_parse.link.url}获取目标剧集")
        root = link_parse.root
        latest_info = movie.get_latest_episode_info()
        if not latest_info:
            logger.debug(f"[{movie.title}] 无最新剧集信息，跳过")
            return None
        latest = latest_info.episode_number
        season_needed = getattr(movie, "season", None)

        groups = {}  # key -> [files]
        container_map = {}  # key -> container
        found_fake = False

        def collect(container, f):
            key = getattr(container, "id", None) or id(container)
            groups.setdefault(key, []).append(f)
            container_map.setdefault(key, container)
            logger.debug(f"收集文件: container={getattr(container, 'name', None)} file={getattr(f, 'name', None)}")

        async def descend(node, container):
            nonlocal found_fake
            if found_fake:
                return

            # 文件
            if not getattr(node, "is_folder", False):
                std = await node.standardized if getattr(node, "standardized", None) is not None else None
                if std and std.resource_type == ResourceType.FILE_EPISODE:
                    ep = std.episode_number
                    if ep is not None and ep > latest:
                        logger.debug(f"发现超前集 fake: file={node.name} ep={ep} latest={latest}")
                        found_fake = True
                        return
                    collect(container, node)
                return

            # 文件夹
            children = []
            if getattr(node, "children", None) is not None:
                children = await node.children or []
            children = [c for c in children if c is not None]
            logger.debug(f"进入文件夹: {getattr(node, 'name', None)} 子项数={len(children)}")

            # 1) 单子文件夹 -> 直接进入
            if len(children) == 1 and getattr(children[0], "is_folder", False):
                logger.debug(f"唯一子文件夹，继续深入: {children[0].name}")
                await descend(children[0], children[0])
                return

            # 2) season 文件夹优先
            season_folder = None
            for c in children:
                if getattr(c, "is_folder", False):
                    std = await c.standardized if getattr(c, "standardized", None) is not None else None
                    if std and std.resource_type == ResourceType.FOLDER_SEASON:
                        sn = getattr(std, "season_number", None)
                        logger.debug(f"检测到季文件夹: {c.name} season={sn}")
                        if sn is not None and season_needed is not None:
                            if int(sn) == int(season_needed):
                                logger.debug(f"匹配到目标季: {season_needed}")
                                season_folder = c
                                break
                        else:
                            season_folder = c
            if season_folder:
                await descend(season_folder, season_folder)
                return

            # 3) quality 文件夹
            q_folders = []
            for c in children:
                if getattr(c, "is_folder", False):
                    std = await c.standardized if getattr(c, "standardized", None) is not None else None
                    if std and std.resource_type == ResourceType.FOLDER_QUALITY:
                        q_folders.append(c)
            if q_folders:
                best = None
                best_rank = -1
                for f in q_folders:
                    std = await f.standardized if getattr(f, "standardized", None) is not None else None
                    q = std.quality if std and getattr(std, "quality", None) else self._guess_quality_from_name(
                        getattr(f, "name", "") or "")
                    r = self._quality_rank(q)
                    logger.debug(f"候选画质文件夹: {f.name} quality={q} rank={r}")
                    if r > best_rank:
                        best_rank = r
                        best = f
                if best:
                    logger.debug(f"进入最佳画质文件夹: {best.name} rank={best_rank}")
                    await descend(best, best)
                    return

            # 4) 遍历子项
            for c in children:
                if not getattr(c, "is_folder", False):
                    std = await c.standardized if getattr(c, "standardized", None) is not None else None
                    if std and std.resource_type == ResourceType.FILE_EPISODE:
                        ep = std.episode_number
                        if ep is not None and ep > latest:
                            logger.debug(f"发现超前集 fake: file={c.name} ep={ep} latest={latest}")
                            found_fake = True
                            return
                        collect(node, c)
                else:
                    std = await c.standardized if getattr(c, "standardized", None) is not None else None
                    if std and std.resource_type == ResourceType.FOLDER_OTHER:
                        logger.debug(f"跳过无效文件夹: {c.name}")
                        continue
                    await descend(c, c)
                    if found_fake:
                        return

        # 开始递归
        logger.debug(f"开始解析: root={getattr(root, 'name', None)} latest={latest} season_needed={season_needed}")
        await descend(root, root)

        if found_fake:
            logger.debug("中止: 检测到 fake 资源")
            return None
        if not groups:
            logger.debug("中止: 未找到有效剧集文件")
            return None

        # 生成候选
        candidates = []
        for key, files in groups.items():
            container = container_map.get(key)
            best_q = None
            best_rank = -1
            max_ep = None
            for f in files:
                std = await f.standardized if getattr(f, "standardized", None) is not None else None
                q = std.quality if std and getattr(std, "quality", None) else self._guess_quality_from_name(
                    getattr(f, "name", "") or "")
                r = self._quality_rank(q)
                if r > best_rank:
                    best_rank = r
                    best_q = q
                ep = std.episode_number if std else None
                if ep is not None:
                    if max_ep is None or ep > max_ep:
                        max_ep = ep
            logger.debug(
                f"候选容器: {getattr(container, 'name', None)} max_ep={max_ep} best_quality={best_q} rank={best_rank}")
            candidates.append((container, files, best_rank, max_ep, best_q.upper() if best_q else None))

        # 排序
        candidates.sort(key=lambda t: ((1 if (t[3] and t[3] >= latest) else 0), t[2], t[3] or 0), reverse=True)
        best_container, best_files, _, best_max_ep, best_q = candidates[0]
        logger.debug(f"最终选择容器: {getattr(best_container, 'name', None)} max_ep={best_max_ep} quality={best_q}")

        return TargetEpisode(share_files=best_files, link_parse=link_parse)


    async def get_target_episode(self, movie: Movie, link_parses: AsyncCachedIterator[LinkParse]):
        async for lp in link_parses:
            print(f'开始：--- {lp.link.title} {lp.link.url}')
            res = await self._get_target_episode(movie, lp)
            if res:
                logger.info(f'获取到目标链接：{res.link_parse.link.url}')
                yield res



target_episode_filter = TargetEpisodeFilter()
async def demo():
    from app.flow.sync_new_movie_flow import link_scraping, link_parse

    await init_db()
    setup_logging()
    print('开始')
    movie=await movie_repository.find_by_douban_id('37040794')
    scrape_results= await link_scraping([movie],count=10)
    parses_results = await link_parse([PrepareParseLinks(scrape_quark_links=s.quark_links,movie=s.movie)for s in scrape_results])
    episode_filter_result= await target_episode_filter.filter(parses_results)


    ...
if __name__ == '__main__':
    asyncio.run(demo())
