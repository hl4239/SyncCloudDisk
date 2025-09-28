# app/api/v1/routers/movies.py
import logging
from datetime import datetime
from typing import Optional, List, Any, Dict, Literal

from fastapi import (
    APIRouter,
    HTTPException,
    Body,
    Path,
    Query,
    Request,
    Response,
    status,
)
from pydantic import BaseModel, Field
# from beanie import PydanticObjectId  # 不再需要按 ObjectId 查找

from app.database.models import (
    Movie,
    EpisodesInfo,
    MovieCloudInfo,
    TMDBInfos,
    MovieType,
    TVCategory,
    MovieCategory,
)
from app.database.movie_repository import movie_repository

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------- Pydantic models for request/response (API layer) ----------
class EpisodeCreate(BaseModel):
    episode_number: int = Field(..., description="集数编号")
    air_date: Optional[str] = Field(None, description="播出日期，YYYY-MM-DD")
    air_time: Optional[str] = Field(None, description="播出时间（ISO string 如 '20:00:00'）")


class EpisodePatch(BaseModel):
    air_date: Optional[Optional[str]] = None
    air_time: Optional[Optional[str]] = None


class TMDBInfosCreate(BaseModel):
    id: Optional[int] = None
    season_number: Optional[int] = None
    not_ensure: Optional[bool] = False


class MovieCloudInfoCreate(BaseModel):
    pancloud_name: Optional[str] = None
    last_save_time: Optional[datetime] = Field(None)
    last_save_link: Optional[str] = Field(None)
    last_save_success: bool = Field(default=False)
    pdir_name: Optional[str] = Field(default=None, )
    latest_episode_number: Optional[int] = Field(default=None)
    share_link:Optional[str] = Field(default=None)

class MoviePatch(BaseModel):
    # 部分更新：douban_id 禁止出现在 payload（不可修改）
    title: Optional[str] = None
    subtitle: Optional[List[str]] = None
    season: Optional[str] = None
    total_episodes: Optional[str] = None
    cloud_infos: Optional[List[MovieCloudInfoCreate]] = None
    tmdb_infos: Optional[TMDBInfosCreate] = None
    episodes_info: Optional[List[EpisodeCreate]] = None
    share_links:Optional[List[str]] = Field(default=None)

class EpisodeResponse(BaseModel):
    episode_number: int
    air_date: Optional[str] = None
    air_time: Optional[str] = None


class MovieResponse(BaseModel):
    douban_id: str
    title: Optional[str] = None
    subtitle: Optional[List[str]] = None
    title_season: Optional[str] = None
    description: Optional[str] = None
    year: Optional[str] = None
    category: Optional[str] = None
    movie_type: MovieType
    season: Optional[str] = None
    total_episodes: Optional[str] = None
    episodes_info: Optional[List[EpisodeResponse]] = None
    tmdb_infos: Optional[TMDBInfosCreate] = None
    cloud_infos: Optional[List[MovieCloudInfoCreate]] = None
    share_links:Optional[List[str]] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None



class ActionResponse(BaseModel):
    ok: bool
    detail: str


# ---------- helpers ----------
def _episodes_model_to_response(episodes: Optional[List[EpisodesInfo]]) -> Optional[List[Dict[str, Any]]]:
    if not episodes:
        return []
    out = []
    for ep in episodes:
        d = {
            "episode_number": ep.episode_number,
            "air_date": ep.air_date.isoformat() if getattr(ep, "air_date", None) else None,
            "air_time": ep.air_time if getattr(ep, "air_time", None) else None,
        }
        out.append(d)
    return out


def _cloudinfos_model_to_response(
    clouds: Optional[List[MovieCloudInfo]],
) -> Optional[List[Dict[str, Any]]]:
    """
    将数据库中的 MovieCloudInfo 列表序列化为 API 响应格式。
    - 确保 path 被强制转换为 str
    - 把所有反斜杠 '\' 规范为 '/'
    """
    if not clouds:
        return []

    out: List[Dict[str, Any]] = []

    for c in clouds:
        last_save_link = str(c.last_save_link).replace("\\", "/") if c.last_save_link else None
        pdir_name = str(c.pdir_name).replace("\\", "/") if c.pdir_name else None

        out.append(
            {
                "pancloud_name": c.pancloud_name,
                "last_save_time": c.last_save_time,
                "last_save_link": last_save_link,
                "last_save_success": c.last_save_success,
                "pdir_name": pdir_name,
                "latest_episode_number": c.latest_episode_number,
                "share_link":c.share_link,
            }
        )

    return out



def _doc_to_response(doc: Movie) -> Dict[str, Any]:
    return {
        "douban_id": doc.douban_id,
        "title": doc.title,
        "subtitle": doc.subtitle,
        "title_season": doc.title_season,
        "description": doc.description,
        "year": doc.year,
        "category": doc.category.value if doc.category is not None else None,
        "movie_type": doc.movie_type,
        "season": doc.season,
        "total_episodes": doc.total_episodes,
        "episodes_info": _episodes_model_to_response(doc.episodes_info),
        "tmdb_infos": {
            "id": getattr(doc.tmdb_infos, "id", None),
            "season_number": getattr(doc.tmdb_infos, "season_number", None),
            "not_ensure": getattr(doc.tmdb_infos, "not_ensure", None),
        }
        if getattr(doc, "tmdb_infos", None)
        else None,
        "cloud_infos": _cloudinfos_model_to_response(doc.cloud_infos),
        "share_links": doc.share_links,
        "create_time": doc.create_time,
        "update_time": doc.update_time,
    }


def _action_ok(detail: str) -> Dict[str, Any]:
    return {"ok": True, "detail": detail}


@router.get("", response_model=List[MovieResponse])
async def list_movies(
    movie_type: Optional[MovieType] = Query(None, description="按 movie_type 过滤"),
    category: Optional[str] = Query(None, description="按 category 过滤"),
    year: Optional[str] = Query(None, description="按 year 过滤"),
    sort_by: Literal["update_time", "create_time", "year"] = Query(
        "update_time", description="排序字段：update_time/create_time/year"
    ),
    sort_order: Literal["asc", "desc"] = Query("desc", description="排序方向：asc 或 desc"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    列表：支持按 movie_type / category / year 过滤，支持按 create_time/update_time/year/title 排序，并支持 offset/limit 分页。
    默认：按 update_time 倒序（最新的在前）。
    """
    filters = {}
    if movie_type is not None:
        filters["movie_type"] = movie_type
    if category is not None:
        filters["category"] = category
    if year is not None:
        filters["year"] = year

    q = Movie.find(filters)

    # 构建 sort 规则
    direction = -1 if sort_order == "desc" else 1
    q = q.sort([(sort_by, direction)])  # Beanie / Motor 应接受类似 pymongo 的 sort 规范

    docs = await q.skip(offset).limit(limit).to_list()
    return [_doc_to_response(d) for d in docs]
@router.get("/today", response_model=List[MovieResponse])
async def today_movies():
    docs=await movie_repository.find_movies_with_episode_today()


    return [_doc_to_response(d) for d in docs]




@router.get("/{douban_id}", response_model=MovieResponse, name="get_movie")
async def get_movie(douban_id: str = Path(..., description="Movie 的 douban_id（唯一）")):
    doc = await Movie.find_one({"douban_id": douban_id})
    if not doc:
        raise HTTPException(status_code=404, detail="not found")
    return _doc_to_response(doc)


# PATCH: 部分更新（严格禁止 douban_id 出现在 payload）
@router.patch("/{douban_id}", response_model=ActionResponse)
async def patch_movie(
    douban_id: str = Path(..., description="Movie 的 douban_id（唯一）"),
    body: MoviePatch = Body(...),
    request: Request = None,
):
    raw = await request.json()
    if "douban_id" in raw:
        raise HTTPException(status_code=400, detail="douban_id is immutable and cannot be changed")

    doc = await Movie.find_one({"douban_id": douban_id})
    if not doc:
        raise HTTPException(status_code=404, detail="not found")

    # 使用 Pydantic v2 的 model_fields_set 检测哪些字段出现在 payload 中
    provided = getattr(body, "model_fields_set", set())

    if "title" in provided:
        doc.title = body.title

    if "subtitle" in provided:
        doc.subtitle = body.subtitle

    if "season" in provided:
        doc.season = body.season

    if "total_episodes" in provided:
        doc.total_episodes = body.total_episodes

    if "tmdb_infos" in provided and body.tmdb_infos is not None:
        # 如果客户端显式传 null -> body.tmdb_infos is None
        doc.tmdb_infos = TMDBInfos(**body.tmdb_infos.model_dump())

    if "cloud_infos" in provided:
        # cloud_infos 是列表，每个元素是 Pydantic 模型或 None
        if body.cloud_infos is None:
            ...
        else:
            # 逐项转换为你在 DB 中期望的对象（这里用 MovieCloudInfo 构造）
            doc.cloud_infos = [MovieCloudInfo(**c.model_dump()) for c in body.cloud_infos]

    if "episodes_info" in provided:
        if body.episodes_info is None:
            ...
        else:
            doc.episodes_info = [EpisodesInfo(**e.model_dump()) for e in body.episodes_info]
    if "share_links" in provided:
        if body.share_links is None:
            ...
        else:
            doc.share_links = body.share_links

    # 更新 update_time（可选，根据你的需求）
    import pytz

    doc.update_time = datetime.now(pytz.timezone("Asia/Shanghai"))

    await doc.save()
    return _action_ok("updated")


@router.delete("/{douban_id}", response_model=ActionResponse)
async def delete_movie(douban_id: str = Path(..., description="Movie 的 douban_id（唯一）")):
    doc = await Movie.find_one({"douban_id": douban_id})
    if not doc:
        raise HTTPException(status_code=404, detail="not found")
    await doc.delete()
    return _action_ok("deleted")
