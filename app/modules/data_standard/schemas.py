# schemas.py（片段：QualityInfo 与 StandardizedResult）
import re
from enum import Enum
from typing import Optional, List, Set, Dict
from pydantic import BaseModel, computed_field, Field

class ResourceType(str, Enum):
    FOLDER_RANGE = "folder:range"
    FOLDER_SEASON = "folder:season"
    FOLDER_QUALITY = "folder:quality"
    FOLDER_OTHER = "folder:other"
    FILE_EPISODE = "file:episode"
    FILE_OTHER = "file:other"
    FILE_RANGE = "file:range"
# --- 静态方法区域 ---
_RESOLUTION_SCORES: Dict[str, int] = {"4K": 4, "2160P": 4, "1440P": 3, "1080P": 2, "720P": 1}
_SOURCE_SCORES: Dict[str, int] = {"BLURAY": 5, "REMUX": 5, "WEB-DL": 4, "WEBRIP": 3, "HDTV": 2, "CAM": 1}
_HDR_SCORES: Dict[str, int] = {"DOLBY VISION": 3, "HDR10+": 2, "HDR10": 1, "HDR": 1}
class QualityInfo(BaseModel):
    resolution: Optional[str] = Field(None, description="2160P/4K/1080P 等")
    fps: Optional[int] = Field(None, description="帧率，如 60")
    hdr: Optional[str] = Field(None, description="HDR10 / DOLBY VISION 等")
    source: Optional[str] = Field(None, description="WEB-DL / BLURAY / REMUX 等")
    codec: Optional[str] = Field(None, description="x264 / x265 / AV1 等")
    audio: Optional[str] = Field(None, description="DTS-HD MA / AC3 等")
    audio_channels: Optional[str] = Field(None, description="声道, 如 5.1 / 7.1")
    bitrate: Optional[str] = Field(None, description="码率字符串，如 10mbps")

    def as_string(self) -> Optional[str]:
        """返回以 '.' 作为分隔符的紧凑质量字符串，或 None。"""
        parts: List[str] = []
        # 优先级排序
        if self.resolution: parts.append(self.resolution.upper())
        if self.fps: parts.append(f"{self.fps}FPS")
        if self.hdr: parts.append(self.hdr.upper().replace(" ", ""))
        if self.source: parts.append(self.source.upper())
        if self.codec: parts.append(self.codec.upper())
        if self.audio: parts.append(self.audio.upper().replace(" ", ""))
        if self.audio_channels: parts.append(self.audio_channels)
        if self.bitrate: parts.append(self.bitrate)
        # 发布组通常不包含在质量字符串中，但如果需要可以取消注释下一行
        # if self.release_group: parts.append(f"[{self.release_group}]")
        return ".".join(parts) if parts else None

class StandardizedResult(BaseModel):
    original_name: Optional[str] = Field(None)
    episode_number: Optional[int] = Field(None)
    season_number: Optional[int] = Field(None)

    # 兼容旧字段（简短字符串）
    quality: Optional[str] = Field(None)
    # 结构化 quality 信息（首选）
    quality_info: Optional[QualityInfo] = Field(None)

    is_special_episode_name: Optional[bool] = Field(False)

    # 统一的范围字段（file/folder 共用）
    episode_start: Optional[int] = Field(None)
    episode_end: Optional[int] = Field(None)
    # 来源：'file' | 'folder' | None
    episode_range_scope: Optional[str] = Field(None)

    is_folder: Optional[bool] = Field(False)

    # 只适用于文件类型，因为文件夹可能包含多个应该用folder_resource_type代替
    resource_type: Optional[ResourceType] = Field(None)

    @computed_field
    @property
    def is_valid(self) -> bool:
        return (
            (self.episode_number is not None)
            or bool(self.is_special_episode_name)
            or (self.episode_start is not None and self.episode_end is not None)
        )

    @computed_field
    @property
    def folder_resource_type(self)->List[ResourceType]:
        result=[]
        if not self.is_folder:
            return result
        if self.season_number:
            result.append(ResourceType.FOLDER_SEASON)
        if self.quality_info:
            result.append(ResourceType.FOLDER_QUALITY)
        if self.episode_start and self.episode_end:
            result.append(ResourceType.FOLDER_RANGE)
        if not result:
            result.append(ResourceType.FOLDER_OTHER)
        return result



    @computed_field
    @property
    def suffix(self) -> Optional[str]:
        if not self.original_name:
            return None
        lowered = (self.original_name or "").lower()
        common_exts = [
            "mkv", "mp4", "avi", "mov", "m4v", "wmv", "flv",
            "torrent", "srt", "ass", "sub", "mp3", "aac", "zip"
        ]
        for ext in common_exts:
            if re.search(r'\.' + re.escape(ext) + r'(?:$|[\s)\]\}])', lowered):
                return ext
        fallback = re.findall(r'\.([a-z0-9]{1,6})(?:$|[\s)\]\},])', lowered, flags=re.I)
        return fallback[-1].lower() if fallback else None

    def _clean_original_name(self) -> str:
        """轻度清理 original_name：去掉外层空白与多重空格。"""
        if not self.original_name:
            return ""
        s = self.original_name.strip()
        # remove surrounding parentheses/brackets if they only wrap the name
        if (s.startswith("(") and s.endswith(")")) or (s.startswith("[") and s.endswith("]")):
            s = s[1:-1].strip()
        # collapse multiple spaces
        s = re.sub(r'\s+', ' ', s)
        return s

    def _to_dot_token(self, s: str) -> str:
        """
        把字符串转为点分隔的 token 形式：
        - 将空白或连续空白替换为单个点
        - 去掉多余的点
        """
        if not s:
            return s
        t = re.sub(r'\s+', '.', s.strip())
        # collapse multiple dots
        t = re.sub(r'\.{2,}', '.', t)
        # trim leading/trailing dots
        t = t.strip('.')
        return t

    @computed_field
    @property
    def standardized_name(self) -> Optional[str]:
        """
        通用标准化命名（使用 '.' 作为分隔符）。
        返回示例：
          - 单集（含季）： "S02E05.1080P.x264.mkv"
          - 单集（无季）： "05.1080P.mkv"
          - 范围（含季，folder）： "S02.E01-E24.1080P"
          - 范围（含季，file）： "S02E01-E03.1080P.mkv"
          - 范围（无季）： "01-12.1080P"
          - 特殊集： "番外篇-角色访谈.1080P.mp4"
        """
        # select quality string (点分隔)
        qstr = None
        if self.quality_info:
            qstr = self.quality_info.as_string()
        elif self.quality:
            # 若旧字段存在，把空白替换为点以兼容
            qstr = self._to_dot_token(self.quality)

        suf = self.suffix

        parts: List[str] = []

        # 1) 范围优先
        if self.episode_start is not None and self.episode_end is not None:
            s = int(self.episode_start)
            e = int(self.episode_end)
            if self.season_number is not None:
                # 使用 Sxx.Eyy-Ezz 或 SxxEyy-Ezz（文件时更紧凑）
                if self.is_folder:
                    parts.append(f"S{int(self.season_number):02d}")
                    parts.append(f"E{s:02d}-E{e:02d}")
                else:
                    parts.append(f"S{int(self.season_number):02d}E{s:02d}-E{e:02d}")
            else:
                parts.append(f"{s:02d}-{e:02d}")

            if qstr:
                parts.append(qstr)
            base = ".".join(parts)

            # 文件需要加后缀
            if not self.is_folder and suf:
                base = f"{base}.{suf}"
            return base

        # 2) 特殊集：保留原名（用点分隔），并附加 quality / suffix
        if self.is_special_episode_name:
            cleaned = self._clean_original_name()
            base = self._to_dot_token(cleaned) or ""
            if qstr and qstr.lower() not in base.lower():
                base = f"{base}.{qstr}" if base else qstr
            if not self.is_folder and suf and not base.lower().endswith(f".{suf}"):
                base = f"{base}.{suf}" if base else f".{suf}"
            return base or None

        # 3) 单集
        if self.episode_number is not None:
            ep = int(self.episode_number)
            if self.season_number is not None:
                parts.append(f"S{int(self.season_number):02d}E{ep:02d}")
            else:
                parts.append(f"{ep:02d}")
            if qstr:
                parts.append(qstr)
            base = ".".join(parts)
            if not self.is_folder and suf:
                base = f"{base}.{suf}"
            return base

        # 4) 仅 season（folder）
        if self.is_folder and self.season_number is not None:
            base = f"Season{int(self.season_number):02d}"
            if qstr:
                base = f"{base}.{qstr}"
            return base

        # 5) 回退到清理后的原名（点替换）
        cleaned = self._clean_original_name()
        if not cleaned:
            return None
        base = self._to_dot_token(cleaned)
        if qstr and qstr.lower() not in base.lower():
            base = f"{base}.{qstr}"
        if not self.is_folder and suf and not base.lower().endswith(f".{suf}"):
            base = f"{base}.{suf}"
        return base

    # --- 静态方法区域 ---
    @staticmethod
    def get_unique_episode_numbers(results: List['StandardizedResult']) -> List[int]:
        """
        从一个 StandardizedResult 列表中计算并返回所有唯一的、已排序的集数，
        此方法会正确地将范围内的所有集数展开。

        Args:
            results: 一个 StandardizedResult 对象的列表。

        Returns:
            一个包含所有不重复集数的、升序排列的整数列表。
        """
        episode_numbers: Set[int] = set()
        for result in results:
            # 条件1：处理单集
            if result.episode_number is not None:
                episode_numbers.add(result.episode_number)

            # 条件2：处理范围
            elif result.episode_start is not None and result.episode_end is not None:
                # 使用 set.update 高效地添加一个范围内的所有数字
                episode_numbers.update(range(result.episode_start, result.episode_end + 1))

        return sorted(list(episode_numbers))

    @staticmethod
    def filter_by_episode_numbers(
            results: List['StandardizedResult'],
            episode_numbers_to_find: List[int]
    ) -> List['StandardizedResult']:
        """
        根据给定的集数列表，筛选一个 StandardizedResult 列表。
        此方法现在可以正确处理单集和范围（如 file:range）。

        Args:
            results: 用于被搜索的 StandardizedResult 对象列表。
            episode_numbers_to_find: 一个包含目标集数（整数）的列表。

        Returns:
            一个新的列表，其中包含 episode_number 匹配或其范围包含任一目标集数的
            StandardizedResult 对象。
        """
        target_episode_set = set(episode_numbers_to_find)
        if not target_episode_set:
            return []

        filtered_list = [
            result for result in results
            if (
                # 条件1：单集直接匹配
                    (result.episode_number is not None and result.episode_number in target_episode_set)
                    or
                    # 条件2：范围包含匹配
                    (
                            result.episode_start is not None and result.episode_end is not None and
                            # 使用 any() 高效检查是否有任何目标集数落在范围内
                            any(result.episode_start <= target_ep <= result.episode_end for target_ep in
                                target_episode_set)
                    )
            )
        ]

        return filtered_list


    @staticmethod
    def _calculate_quality_score(result: 'StandardizedResult') -> int:
        """根据 resolution, source, hdr 等计算一个综合质量得分，用于排序。"""
        if not result.quality_info:
            return 0
        score = 0
        qi = result.quality_info
        if qi.resolution:
            score += _RESOLUTION_SCORES.get(qi.resolution.upper(), 0) * 10
        if qi.source:
            score += _SOURCE_SCORES.get(qi.source.upper(), 0) * 5
        if qi.hdr:
            score += _HDR_SCORES.get(qi.hdr.upper(), 0) * 3
        return score

    @staticmethod
    def find_optimal_coverage(
            results: List['StandardizedResult'],
            required_episodes: List[int],
            preferred_suffixes: Optional[List[str]] = None
    ) -> List['StandardizedResult']:
        """
        根据给定的剧集需求，找到满足条件的最优文件组合。
        优化优先级: 1.首选后缀名 2.最少文件数(最大覆盖) 3.最高画质

        Args:
            results: 所有可用的 StandardizedResult 对象列表。
            required_episodes: 需要满足的集数列表。
            preferred_suffixes: 一个包含优先选择的文件后缀名（如 ['mkv', 'mp4']）的列表。

        Returns:
            一个 StandardizedResult 对象的列表，代表最优的文件选择。
        """
        episodes_to_find = set(required_episodes)
        # 为了高效查找，将后缀名列表转为集合，并统一为小写
        preferred_set = set(s.lower() for s in preferred_suffixes) if preferred_suffixes else set()
        selected_results: List[StandardizedResult] = []

        while episodes_to_find:
            best_candidate: Optional[StandardizedResult] = None
            # 使用元组来存储最优选择的评分，格式为: (后缀匹配, 覆盖数, 画质分)
            best_choice_tuple = (-1, -1, -1)

            for candidate in results:
                if candidate in selected_results:
                    continue

                provided_episodes: Set[int] = set()
                if candidate.episode_number is not None:
                    provided_episodes.add(candidate.episode_number)
                elif candidate.episode_start is not None and candidate.episode_end is not None:
                    provided_episodes.update(range(candidate.episode_start, candidate.episode_end + 1))

                coverage = episodes_to_find.intersection(provided_episodes)
                coverage_count = len(coverage)

                if coverage_count == 0:
                    continue

                # --- 决策核心修改 ---
                # 1. 计算后缀名得分
                suffix_score = 1 if preferred_set and candidate.suffix and candidate.suffix.lower() in preferred_set else 0

                # 2. 计算画质得分
                quality_score = StandardizedResult._calculate_quality_score(candidate)

                # 3. 组成决策元组
                candidate_tuple = (suffix_score, coverage_count, quality_score)

                # 4. 比较元组，Python会按顺序比较元组内的元素
                if candidate_tuple > best_choice_tuple:
                    best_choice_tuple = candidate_tuple
                    best_candidate = candidate

            if not best_candidate:
                break

            selected_results.append(best_candidate)

            covered_by_best: Set[int] = set()
            if best_candidate.episode_number is not None:
                covered_by_best.add(best_candidate.episode_number)
            elif best_candidate.episode_start is not None and best_candidate.episode_end is not None:
                covered_by_best.update(range(best_candidate.episode_start, best_candidate.episode_end + 1))

            episodes_to_find.difference_update(covered_by_best)

        return selected_results
