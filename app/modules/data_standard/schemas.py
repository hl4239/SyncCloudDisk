import re
from enum import Enum
from typing import Optional
from pydantic import BaseModel, computed_field, Field

# -------------------------
# ResourceType 枚举
# -------------------------
class ResourceType(str, Enum):
    FOLDER_RANGE = "folder:range"
    FOLDER_SEASON = "folder:season"
    FOLDER_QUALITY = "folder:quality"
    FOLDER_OTHER = "folder:other"
    FILE_EPISODE = "file:episode"
    FILE_OTHER = "file:other"

# -------------------------
# StandardizedResult 数据模型（扩展：resource_type）
# -------------------------
class StandardizedResult(BaseModel):
    original_name: Optional[str] = Field(None)
    episode_number: Optional[int] = Field(None)
    season_number: Optional[int] = Field(None)
    quality: Optional[str] = Field(None)
    is_special_episode_name: Optional[bool] = Field(False)

    # 文件夹相关
    is_folder: Optional[bool] = Field(False)
    folder_episode_start: Optional[int] = Field(None)
    folder_episode_end: Optional[int] = Field(None)

    # 新：资源类型分类（见 ResourceType）
    resource_type: Optional[ResourceType] = Field(None)

    @computed_field
    @property
    def is_valid(self) -> bool:
        return (
            (self.episode_number is not None)
            or bool(self.is_special_episode_name)
            or (self.folder_episode_start is not None and self.folder_episode_end is not None)
        )

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

    @computed_field
    @property
    def standardized_episode_name(self) -> Optional[str]:
        suf = self.suffix
        if self.is_folder and self.folder_episode_start is not None and self.folder_episode_end is not None:
            start = int(self.folder_episode_start)
            end = int(self.folder_episode_end)
            if self.season_number is not None:
                base = f"S{int(self.season_number):02d}E{start:02d}-E{end:02d}"
            else:
                base = f"{start:02d}-{end:02d}"
            if self.quality:
                base = f"{base} {self.quality}"
            return base

        if self.is_special_episode_name:
            base = self.original_name or ""
            if suf and base and not base.lower().endswith(f".{suf}"):
                base = f"{base}.{suf}"
            if self.quality and self.quality.lower() not in (base or "").lower():
                base = f"{base} {self.quality}"
            return base or None

        if self.episode_number is None:
            return None
        if self.season_number is None:
            base = f"{int(self.episode_number):02d}"
        else:
            base = f"S{int(self.season_number):02d}E{int(self.episode_number):02d}"
        if self.quality:
            base = f"{base} {self.quality}"
        if suf:
            base = f"{base}.{suf.lstrip('.').lower()}"
        return base

if __name__ == "__main__":
    samples = [
        StandardizedResult(original_name="S01E102.mkv", episode_number=22, season_number=1),
        StandardizedResult(original_name="02.MP4", episode_number=2),
        StandardizedResult(original_name="Some.Show.E03.1080p.WEB-DL.mkv", episode_number=3, quality="1080P"),
        StandardizedResult(original_name="番外篇 - 角色访谈.mp4", is_special_episode_name=True),
        StandardizedResult(original_name="番外篇 - 角色访谈", is_special_episode_name=True, suffix=None),  # no suffix in original
        StandardizedResult(original_name="Movie.torrent"),
        StandardizedResult(original_name="01-50",is_folder=True),
        StandardizedResult(original_name="weird.name.v1.avi (backup).zip"),
    ]

    for r in samples:
        print(
            f"orig: {r.original_name!r:40} | suffix: {r.suffix!r:8} | is_valid: {r.is_valid} | standardized: {r.standardized_episode_name!r}"
        )
