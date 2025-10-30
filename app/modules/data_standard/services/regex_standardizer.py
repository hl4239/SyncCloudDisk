# regex_standardizer.py (严格匹配并尊重初始值版本)
import asyncio
import logging
import re
from functools import lru_cache
from typing import List, Optional, Tuple

from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.movie_repository import movie_repository
from app.modules.data_standard.interfaces.standardizer_interface import IStandardizer
from app.modules.data_standard.schemas import StandardizedResult, ResourceType, QualityInfo
from app.utils.async_iterator import AsyncCachedIterator

logger = logging.getLogger(__name__)


class RegexStandardizer(IStandardizer):
    # --- 1. 剧集/季/范围匹配规则 (收紧为严格模式) ---
    # 移除了模糊的纯数字匹配，只保留具有明确标识符的模式

    _KNOWN_QUALITY_KEYWORDS = r'(?:4k|2160p|1440p|1080p|720p|bluray|remux|web-dl|webdl|x265|h265|x264|h264)'
    _patterns: List[str] = [
        # 高优先级 SxxExx 格式
        r'\bS(?P<season>\d{1,2})[ ._\-]*E(?P<episode>\d{1,4})\b',
        r'Season[ ._\-]?(?P<season>\d{1,2})[ ._\-]*(?:Ep|Episode)?[ ._\-]?(?P<episode>\d{1,4})\b',
        r'第\s*(?P<season>\d{1,2})\s*季\s*第\s*(?P<episode>\d{1,4})\s*[集话回話]',
        # 带有明确标识符的集数
        r'\bEp[ ._\-]?(?P<episode>\d{1,4})\b',
        r'\b[Ee](?P<episode>\d{1,4})\b',
        r'-\s*(?P<episode>\d{1,4})\s*(?:\[|\.)',  # Show - 01 [1080p] or Show - 01.mkv
        r'第\s*(?P<episode>\d{1,4})\s*[集话回話]',

        # --- 新增的智能模式 ---
        r'\b(?P<episode>\d{1,4})\b\s*[-.丨_ ]\s*' + _KNOWN_QUALITY_KEYWORDS,
    ]

    # 范围和季文件夹的规则保持不变，因为它们本身具有较高的确定性
    _range_patterns: List[str] = [
        r'\bS(?P<season>\d{1,2})[ ._\-]*E(?P<start>\d{1,4})[ ._\-]*-[ ._\-]*E(?P<end>\d{1,4})\b',
        r'第\s*(?P<start>\d{1,4})[ ._\-]*-[ ._\-]*\s*(?P<end>\d{1,4})\s*[集话回]',
        r'(?P<start>\d{1,4})\s*[-_–—~～]\s*(?P<end>\d{1,4})\b',
        r'(?P<count>\d{1,4})\s*集\s*全',
        r'共\s*(?P<count>\d{1,4})\s*集',
    ]

    _season_folder_patterns: List[str] = [
        r'Season[ _-]?\d{1,2}\b',
        r'第\s*\d{1,2}\s*季',
        r'[Ss]\d{1,3}'
    ]

    _special_episode_patterns: List[str] = [
        r'\b(?:番外|ova|sp|special|extra|特典|特辑|ncor|nced|pv|cm)\b'
    ]

    # --- 2. 质量/元数据提取规则 (保持不变) ---
    _QUALITY_REGEX_MAP: List[Tuple[str, str]] = [
        ("resolution", r'\b(4k|2160p|1440p|1080p|720p|480p)\b|\b(\d{3,4}x\d{3,4})\b'),
        ("fps", r'\b(\d{2,3}(?:\.\d{1,3})?)\s*(fps|hz|帧|帧率)\b'),
        ("hdr", r'\b(hdr10\+|hdr10|dolby\s*vision|dolbyvision|dv|hdr)\b'),
        ("source", r'\b(web-dl|webdl|webrip|bluray|blu-ray|bdrip|remux|hdtv|dvdrip|cam|ts)\b'),
        ("codec", r'\b(x265|h265|hevc|x264|h264|avc|av1|vp9)\b'),
        ("audio", r'\b(dts-hd\s*ma|dts-hd|dts|truehd|atmos|eac3|ac3|aac|flac|opus)\b'),
        ("audio_channels", r'\b([579]\.1)\b'),
        ("bitrate", r'\b(\d+(?:\.\d+)?(?:kbps|mbps))\b'),
    ]


    # --- 3. 规范化映射字典 (保持不变) ---
    _SOURCE_MAP = {"web-dl": "WEB-DL", "webdl": "WEB-DL", "webrip": "WEBRIP", "bluray": "BLURAY", "blu-ray": "BLURAY",
                   "bdrip": "BLURAY", "remux": "REMUX", "hdtv": "HDTV", "dvdrip": "DVDRIP", "cam": "CAM", "ts": "CAM"}
    _CODEC_MAP = {"x265": "x265", "h265": "x265", "hevc": "x265", "x264": "x264", "h264": "x264", "avc": "x264",
                  "av1": "AV1", "vp9": "VP9"}
    _HDR_MAP = {"hdr10+": "HDR10+", "hdr10": "HDR10", "dolby vision": "DOLBY VISION", "dolbyvision": "DOLBY VISION",
                "dv": "DOLBY VISION", "hdr": "HDR"}
    _AUDIO_MAP = {"dts-hd ma": "DTS-HD MA", "dts-hd": "DTS-HD", "dts": "DTS", "truehd": "TrueHD", "atmos": "ATMOS",
                  "eac3": "EAC3", "ac3": "AC3", "aac": "AAC", "flac": "FLAC", "opus": "OPUS"}

    @classmethod
    @lru_cache(maxsize=1)
    def _compiled_patterns(cls):
        flags = re.I
        return {
            "patterns": [re.compile(p, flags) for p in cls._patterns],
            "range_patterns": [re.compile(p, flags) for p in cls._range_patterns],
            "season_folder_patterns": [re.compile(p, flags) for p in cls._season_folder_patterns],
            "special_episode_patterns": [re.compile(p, flags) for p in cls._special_episode_patterns],
            "quality_map": [(field, re.compile(pattern, flags)) for field, pattern in cls._QUALITY_REGEX_MAP],
        }

    @classmethod
    def _extract_metadata(cls, text: str) -> Tuple[QualityInfo, str]:
        # 此方法逻辑保持不变，因为它只负责提取和清理
        qi = QualityInfo()
        working_text = f" {text.lower()} "



        for field, pattern in cls._compiled_patterns()["quality_map"]:
            matches = list(pattern.finditer(working_text))
            if not matches: continue
            match = matches[0]
            val = next((g for g in match.groups() if g is not None), None)
            if not val: continue

            working_text = working_text.replace(match.group(0), " ")
            val_lower = val.replace(" ", "")
            if field == "resolution":
                if "x" in val_lower:
                    try:
                        w, h = map(int, val_lower.split('x'))
                        if h >= 2160:
                            qi.resolution = "4K"
                        elif h >= 1440:
                            qi.resolution = "1440P"
                        elif h >= 1080:
                            qi.resolution = "1080P"
                        elif h >= 720:
                            qi.resolution = "720P"
                    except ValueError:
                        pass
                else:
                    qi.resolution = "4K" if "4k" in val_lower or "2160" in val_lower else val_lower.upper()
            elif field == "fps":
                qi.fps = int(float(val))
            elif field == "hdr":
                qi.hdr = cls._HDR_MAP.get(val_lower, val_lower.upper())
            elif field == "source":
                qi.source = cls._SOURCE_MAP.get(val_lower, val_lower.upper())
            elif field == "codec":
                qi.codec = cls._CODEC_MAP.get(val_lower, val_lower.upper())
            elif field == "audio":
                qi.audio = cls._AUDIO_MAP.get(val_lower, val_lower.upper())
            elif field == "audio_channels":
                qi.audio_channels = val
            elif field == "bitrate":
                qi.bitrate = val

        cleaned_text = re.sub(r'\s+', ' ', working_text).strip()
        cleaned_text = re.sub(r'[\[\]\(\)]', ' ', cleaned_text).strip()
        return qi, cleaned_text

    @classmethod
    def _standardize_one(cls, item: StandardizedResult) -> StandardizedResult:
        original_name = (item.original_name or "").strip()
        compiled = cls._compiled_patterns()

        # 步骤 1: 提取元数据。总是执行以获得清理后的名称，但仅在 item.quality_info 为空时赋值
        quality_info, cleaned_name = cls._extract_metadata(original_name)
        if item.quality_info is None and any(quality_info.model_dump().values()):
            item.quality_info = quality_info
            item.quality = quality_info.as_string()

        # 步骤 2: 判断资源类型（文件夹 vs 文件）
        if item.is_folder:
            # 2.1 文件夹范围匹配 (仅在未设置时)
            if item.episode_start is None:
                for rp in compiled["range_patterns"]:
                    if m := rp.search(original_name.lower()):
                        gd = m.groupdict()
                        if count := gd.get("count"):
                            item.episode_start, item.episode_end = 1, int(count)
                        elif start := gd.get("start"):
                            item.episode_start, item.episode_end = int(start), int(gd["end"])
                        item.resource_type = ResourceType.FOLDER_RANGE
                        return item

            # 2.2 季文件夹匹配 (仅在未设置时)
            # if item.season_number is None:
            # 强制根据检测到季号的为准
            for sp in compiled["season_folder_patterns"]:
                if sp.search(original_name.lower()):
                    item.resource_type = ResourceType.FOLDER_SEASON
                    if m := re.search(r'(?:season|s)\s*0*?(\d{1,2})', original_name.lower()):
                        item.season_number = int(m.group(1))
                    return item

            # 2.3 其他文件夹类型
            if item.resource_type is None:
                if item.quality_info and not cleaned_name.replace('.', '').strip():
                    item.resource_type = ResourceType.FOLDER_QUALITY
                else:
                    item.resource_type = ResourceType.FOLDER_OTHER
            return item

        # ---------- 文件处理 ----------
        # 步骤 3: 优先级：范围 -> 单集 -> 特殊集

        # 3.1 文件内范围匹配 (仅在未设置时)
        if item.episode_start is None:
            for rp in compiled["range_patterns"]:
                if m := rp.search(original_name.lower()):
                    gd = m.groupdict()
                    if start := gd.get("start"):
                        item.episode_start, item.episode_end = int(start), int(gd["end"])
                        item.episode_range_scope = "file"
                        item.resource_type = ResourceType.FILE_RANGE
                        if item.season_number is None and (season := gd.get("season")):
                            item.season_number = int(season)
                        return item  # 范围匹配成功，直接返回

        # 3.2 单集解析 (仅在未设置时)
        if item.episode_number is None:
            for pat in compiled["patterns"]:
                if m := pat.search(original_name):
                    gd = m.groupdict()
                    # 只要匹配到 episode，就认为成功，并填充所有可用的信息
                    if ep_str := gd.get("episode"):
                        item.episode_number = int(ep_str)
                        if item.season_number is None and (sn_str := gd.get("season")):
                            item.season_number = int(sn_str)
                        break  # 找到第一个确定性的匹配就停止

        # 3.3 特殊集名识别 (仅在常规集数未被设置或找到时)
        if item.episode_number is None and item.is_special_episode_name is not True:
            is_special = any(pat.search(original_name.lower()) for pat in compiled["special_episode_patterns"])
            if is_special:
                item.is_special_episode_name = True

        # 步骤 4: 分配最终的资源类型 (仅在未设置时)
        if item.resource_type is None:
            if item.episode_number is not None or item.is_special_episode_name:
                item.resource_type = ResourceType.FILE_EPISODE
            else:
                item.resource_type = ResourceType.FILE_OTHER
        return item

    @classmethod
    async def standardize(cls, items: List[StandardizedResult]) -> List[StandardizedResult]:
        return [cls._standardize_one(item) for item in items]


# 单例
regex_standardizer = RegexStandardizer()

# -------------------------
# Demo（测试尊重初始值和严格匹配）
# -------------------------
if __name__ == '__main__':
    async def demo():
        # 1. 准备一个资源列表，包含不同后缀和质量
        available_files: List[StandardizedResult] = [
            # 第1集有 MKV 和 MP4 两个版本
            StandardizedResult(original_name="Show.E01.1080p.mp4", episode_number=1,
                               quality_info=QualityInfo(resolution="1080P")),
            StandardizedResult(original_name="Show.E01.1080p.mkv", episode_number=1,
                               quality_info=QualityInfo(resolution="1080P")),

            # 范围文件 2-3，是 MP4
            StandardizedResult(
                original_name="Show.E02-E03.1080p.mp4",
                episode_start=2, episode_end=3,
                quality_info=QualityInfo(resolution="1080P")
            ),
            StandardizedResult(
                original_name="Show.E02-E03.4K.mkv",
                episode_start=2, episode_end=3,
                quality_info=QualityInfo(resolution="4K")
            ),

            # 范围文件 4-5，是 MKV，但质量稍低
            StandardizedResult(
                original_name="Show.E04-E05.720p.mkv",
                episode_start=4, episode_end=5,
                quality_info=QualityInfo(resolution="720P")
            ),
            StandardizedResult(
                original_name="Show.E04-E05.720p.mp4",
                episode_start=4, episode_end=5,
                quality_info=QualityInfo(resolution="720P")
            ),

            # 单独的第6集，是 AVI，我们不想要它
            StandardizedResult(original_name="Show.E06.1080p.avi", episode_number=6,
                               quality_info=QualityInfo(resolution="1080P")),
        ]

        # 2. 定义我们的需求和首选后缀
        required = [1, 2, 3, 4, 5]
        preferred = ['torrent']

        # 3. 调用方法
        optimal_selection = StandardizedResult.find_optimal_coverage(
            results=available_files,
            required_episodes=required,
            preferred_suffixes=preferred
        )

        print(f"需求集数: {required}")
        print(f"首选后缀: {preferred}")
        print("-" * 70)
        print(f"找到的最优文件组合 ({len(optimal_selection)} 个文件):")
        for item in optimal_selection:
            print(f"  - {item.original_name}")

        # --- 期望的输出 ---
        # 需求集数: [1, 2, 3, 4, 5]
        # 首选后缀: ['mkv']
        # ----------------------------------------------------------------------
        # 找到的最优文件组合 (3 个文件):
        #   - Show.E04-E05.720p.mkv     <-- 第一轮被选中，因为它有首选后缀'mkv'且覆盖2集，是所有mkv文件中覆盖最多的。
        #   - Show.E01.1080p.mkv        <-- 第二轮被选中，因为它有首选后缀'mkv'且覆盖了剩下的第1集。
        #   - Show.E02-E03.1080p.mp4    <-- 第三轮，mkv文件已无法满足剩下的2,3集需求，算法回退到选择非首选后缀的文件。
    async def demo1():


        r=StandardizedResult(original_name="01-02",is_folder=True)
        rr= await regex_standardizer.standardize([r])
        print(rr)
    async def demo2():
        from app.modules.link_parse.schemas import PrepareParseLinks

        from app.database.models import CloudShareLink, Movie

        from app.modules.link_parse.services.link_parser import link_parser
        await init_db()
        setup_logging()
        movie=await movie_repository.find_by_douban_id('37211138')
        r=await link_parser.parse_links(links=[PrepareParseLinks(
            scrape_baidu_links=lambda :AsyncCachedIterator([]),
            links=[CloudShareLink(url='https://pan.quark.cn/s/ea48e9e2f72d#/list/share',title='潜能探案组 第二季')],movie=movie)])
        async for i in  r[0].quark_parses:
            print(await(await i.root.children)[0].children)
            for j in await(await i.root.children)[0].children:
                if j.name=='S01':
                    for k in await j.children:
                        print(await k.standardized)
    asyncio.run(demo2())