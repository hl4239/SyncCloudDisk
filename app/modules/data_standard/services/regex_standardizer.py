import asyncio
import logging
import re
from functools import lru_cache
from typing import List

from app.modules.data_standard.interfaces.standardizer_interface import IStandardizer
from app.modules.data_standard.schemas import StandardizedResult, ResourceType
from app.utils.cache import async_ttl_cache

logger = logging.getLogger(__name__)


# -------------------------
# RegexStandardizer（增强版：字符串规则 + 懒编译缓存）
# -------------------------
class RegexStandardizer(IStandardizer):
    """
    基于正则的标准化器并做资源类型分类（文件/文件夹）
    规则以字符串列表保存，通过 _compiled_patterns 懒编译并缓存为 re.Pattern 列表。
    """

    # 剧集文件名匹配规则（按优先级）——以字符串保存
    _patterns: List[str] = [
        r"(?i)\bS(?P<season>\d{1,2})[ ._\-]*E(?P<episode>\d{1,4})\b",
        r'\bS(?P<season>\d{1,2})[ ._\-]*E(?P<episode>\d{1,4})\b',
        r'Season[ _\-]?(?P<season>\d{1,2})[ _\-.]*(?:Ep|Episode)?[ _\-]?(?P<episode>\d{1,4})\b',
        r'\bE(?P<episode>\d{1,4})\b',
        r'\bEp[ ._\-]?(?P<episode>\d{1,4})\b',
        r'第\s*(?P<episode>\d{1,4})\s*[集话回]',
        r'^(?P<episode>\d{1,4})\.(?:mkv|mp4|torrent|avi|m4v)$',
        r'\b(?P<episode>\d{1,4})\b',
        r''
    ]

    # 画质匹配（字符串）
    _quality_patterns: List[str] = [
        r'\b(2160p|1080p|720p|480p)\b',
        r'\b(4k|8k|hd|fhd|uhd|bluray|bdrip|bdr)\b',
        r'\b(web[-_. ]?dl|web[-_. ]?rip|webrip|webrar)\b',
    ]

    # folder range patterns（支持多种连写，字符串形式）
    _folder_range_patterns: List[str] = [
        r'(?P<start>\d{1,4})\s*[-_–—]\s*(?P<end>\d{1,4})',
        r'(?P<start>\d{1,4})\s*[~～]\s*(?P<end>\d{1,4})',
        r'(?P<start>\d{1,4})\s*(?:to)\s*(?P<end>\d{1,4})',
        r'(?P<start>\d{1,4})\s*(?:至|到)\s*(?P<end>\d{1,4})',
        r'\(?\b(?P<start>\d{1,4})\s*[-_–—~～]\s*(?P<end>\d{1,4})\b\)?',
    ]

    # season folder keywords（字符串）
    _season_folder_patterns: List[str] = [
        r'Season[ _-]?\d{1,2}\b',
        r'\bS\d{1,2}\b',
        r'第\s*\d{1,2}\s*季',
        r'\bseason\b',  # 宽松匹配
    ]

    # quality folder keywords (folder 名称中仅包含或以质量词为主)
    _quality_folder_patterns: List[str] = [
        r'^(?:2160p|1080p|720p|480p|4k|8k|hd|fhd|uhd|bluray|bdrip|web-dl|webrip|remux|hdr|dvdrip)\b',
        r'\b(1080p|720p|4k|hd|bluray|web[-_. ]?dl|webrip|remux|hdr)\b',
    ]

    # 媒体文件扩展名（用于区分文件类型）
    _media_exts = {"mkv", "mp4", "avi", "mov", "m4v", "wmv", "flv", "mp3", "aac", "iso"}

    @classmethod
    @lru_cache(maxsize=1)
    def _compiled_patterns(cls):
        """
        把字符串规则编译成 re.Pattern 列表并缓存（只编译一次）。
        默认对大多数模式使用 re.I（忽略大小写），这能替代字符串中 (?i) 的写法。
        """
        flags = re.I  # 全局忽略大小写，通常适合媒体文件名匹配
        try:
            compiled = {
                "patterns": [re.compile(p, flags) for p in cls._patterns],
                "quality_patterns": [re.compile(p, flags) for p in cls._quality_patterns],
                "folder_range_patterns": [re.compile(p, flags) for p in cls._folder_range_patterns],
                "season_folder_patterns": [re.compile(p, flags) for p in cls._season_folder_patterns],
                "quality_folder_patterns": [re.compile(p, flags) for p in cls._quality_folder_patterns],
            }
        except re.error as e:
            # 防御性日志，理论上不会触发
            logger.exception("Compile regex failed: %s", e)
            # 回退到不编译的空结果，避免抛出
            compiled = {
                "patterns": [],
                "quality_patterns": [],
                "folder_range_patterns": [],
                "season_folder_patterns": [],
                "quality_folder_patterns": [],
            }
        return compiled

    @classmethod
    def _standardize_one(cls, item: StandardizedResult) -> StandardizedResult:
        name = (item.original_name or "").strip()
        lowered = name.lower()

        matched = False

        # 获取已编译的 pattern 列表
        compiled = cls._compiled_patterns()
        patterns = compiled["patterns"]
        quality_patterns = compiled["quality_patterns"]
        folder_range_patterns = compiled["folder_range_patterns"]
        season_folder_patterns = compiled["season_folder_patterns"]
        quality_folder_patterns = compiled["quality_folder_patterns"]

        # ---------- 文件夹处理 ----------
        if item.is_folder:
            # 1) 优先判断范围文件夹
            for fr_pat in folder_range_patterns:
                fr = fr_pat.search(lowered)
                if fr:
                    try:
                        start = int(fr.group("start"))
                        end = int(fr.group("end"))
                        if start > end:
                            start, end = end, start
                        item.folder_episode_start = start
                        item.folder_episode_end = end
                        item.resource_type = ResourceType.FOLDER_RANGE
                        matched = True
                        break
                    except (ValueError, IndexError):
                        continue
            if matched:
                # 仍尝试抽取画质
                if item.quality is None:
                    for qpat in quality_patterns:
                        qm = qpat.search(lowered)
                        if qm:
                            item.quality = qm.group(1).upper()
                            break
                return item

            # 2) season 文件夹检测（例如 "Season 02", "第2季", "S02"）
            for sp in season_folder_patterns:
                if sp.search(lowered):
                    item.resource_type = ResourceType.FOLDER_SEASON
                    # 如果 Season 后面有数字，提取 season_number
                    m = re.search(r'(?:season|s)\s*0*?(\d{1,2})', lowered, re.I)
                    if not m:
                        m = re.search(r'第\s*(\d{1,2})\s*季', lowered)
                    if m:
                        try:
                            item.season_number = int(m.group(1))
                        except Exception:
                            pass
                    # 同时检查是否包含范围（如 "Season 02 (01-24)"）
                    for fr_pat in folder_range_patterns:
                        fr = fr_pat.search(lowered)
                        if fr:
                            try:
                                s = int(fr.group("start")); e = int(fr.group("end"))
                                if s > e: s, e = e, s
                                item.folder_episode_start = s
                                item.folder_episode_end = e
                            except Exception:
                                pass
                    # 画质尝试
                    if item.quality is None:
                        for qpat in quality_patterns:
                            qm = qpat.search(lowered)
                            if qm:
                                item.quality = qm.group(1).upper()
                                break
                    return item

            # 3) quality 文件夹检测（例如 "1080p", "WEB-DL", "BluRay"）
            for qf in quality_folder_patterns:
                if qf.search(lowered):
                    item.resource_type = ResourceType.FOLDER_QUALITY
                    # 抽取画质关键词
                    for qpat in quality_patterns:
                        qm = qpat.search(lowered)
                        if qm:
                            item.quality = qm.group(1).upper()
                            break
                    return item

            # 4) 其他文件夹 -> folder:other
            item.resource_type = ResourceType.FOLDER_OTHER
            # 尝试检测是否 folder 名称本身就是合集（合集/全集）
            if re.search(r'\b合集|全集|complete|合集\b', lowered, re.I):
                # 仍可尝试找范围或单个数字
                for fr_pat in folder_range_patterns:
                    fr = fr_pat.search(lowered)
                    if fr:
                        try:
                            s = int(fr.group("start")); e = int(fr.group("end"))
                            if s > e: s, e = e, s
                            item.folder_episode_start = s
                            item.folder_episode_end = e
                            item.resource_type = ResourceType.FOLDER_RANGE
                            break
                        except Exception:
                            pass
            return item

        # ---------- 文件处理 ----------
        # 先尝试从文件名抽取 season/episode（跟你原有逻辑一致）
        for pat in patterns:
            m = pat.search(lowered)
            if not m:
                continue
            gd = m.groupdict()
            ep_str = gd.get("episode")
            if ep_str and item.episode_number is None:
                try:
                    item.episode_number = int(ep_str)
                except ValueError:
                    pass
            sn_str = gd.get("season")
            if sn_str and item.season_number is None:
                try:
                    item.season_number = int(sn_str)
                except ValueError:
                    pass
            matched = True
            break

        # 画质提取（若尚未有 quality）
        if item.quality is None:
            for qpat in quality_patterns:
                qm = qpat.search(lowered)
                if qm:
                    item.quality = qm.group(1).upper()
                    break

        # 判断文件扩展名是否为媒体扩展
        suf = (item.suffix or "").lower()
        is_media_ext = suf in cls._media_exts

        # 特殊集检测（番外/OVA...）
        if re.search(r'番外|ova|special|extra|特典|特辑', lowered, re.I):
            item.is_special_episode_name = True

        # 分类策略：
        # - 如果解析出 episode/season -> file:episode
        # - 或者文件后缀是媒体且文件名含剧集线索 -> file:episode
        # - 否则，如果是媒体扩展但无法识别为剧集，则归入 file:other（可能是电影/合集）
        # - 其他文件 -> file:other
        if item.episode_number is not None or item.is_special_episode_name:
            item.resource_type = ResourceType.FILE_EPISODE
        else:
            # # 如果文件是媒体扩展并且文件名含数字或 "part"/"cd" 之类，仍视为 episode 型资源（宽松策略）
            # if is_media_ext:
            #     if re.search(r'\bpart\s*\d+|\bcd\s*\d+|\bdisc\s*\d+|\b卷\b|\b集\b', lowered, re.I) or re.search(r'\d{1,3}', lowered):
            #         # 虽然电影名也可能包含数字，但为了网盘刮削优先保守标记为媒体资源
            #         item.resource_type = ResourceType.FILE_EPISODE
            #     else:
            #         # 无明显剧集线索，但为媒体文件 -> 仍视为媒体资源（方便人工/后续判断）
            #         item.resource_type = ResourceType.FILE_EPISODE
            # else:
                item.resource_type = ResourceType.FILE_OTHER

        return item

    @classmethod
    async def standardize(cls, items: List[StandardizedResult]) -> List[StandardizedResult]:
        # 对每个条目调用 _standardize_one（同步）并返回
        return [cls._standardize_one(item) for item in items]


# 单例
regex_standardizer = RegexStandardizer()

# -------------------------
# Demo（用于本地测试）
# -------------------------
if __name__ == '__main__':
    async def demo():
        samples = [
            StandardizedResult(original_name="Confidence.Queen.S01E01v2.mp4", is_folder=False),
            StandardizedResult(original_name="Season 02", is_folder=True),
            StandardizedResult(original_name="1080p", is_folder=True),
            StandardizedResult(original_name="Random Documents", is_folder=True),
            StandardizedResult(original_name="S01E02.mkv"),
            StandardizedResult(original_name="Some.Show.E03.1080p.WEB-DL.mkv"),
            StandardizedResult(original_name="Movie Title (2020).mp4"),
            StandardizedResult(original_name="readme.txt"),
            StandardizedResult(original_name="合集 05至08", is_folder=True),
            StandardizedResult(original_name="集数(01~12)", is_folder=True),
            StandardizedResult(original_name="番外篇 - 角色访谈.mp4"),
        ]
        out = await regex_standardizer.standardize(samples)
        for r in out:
            print(
                f"{r.original_name!r:35} | is_folder: {r.is_folder} | resource_type: {r.resource_type} | "
                f"folder_range: {(r.folder_episode_start, r.folder_episode_end)} | season: {r.season_number} | "
                f"episode: {r.episode_number} | quality: {r.quality} | special: {r.is_special_episode_name}"
            )

    asyncio.run(demo())
