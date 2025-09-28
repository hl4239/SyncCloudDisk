import logging
from typing import Optional, List, Any, Dict

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
from beanie import PydanticObjectId  # 保留导入可选；如果未使用可删掉

from app.database.models import CloudType, PanCloud

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------- Pydantic models for request/response ----------

class PanCloudCreate(BaseModel):
    name: Optional[str] = Field(None, description="唯一标识，创建时由用户手动输入")
    cloud_type: CloudType = Field(..., description="网盘类型")
    cookie: Optional[str] = Field(None, description="登录 cookie")
    enable: Optional[bool] = Field(False, description="是否启用该网盘")

class PanCloudReplace(BaseModel):
    name: Optional[str] = Field(None)
    cloud_type: CloudType = Field(...)
    cookie: Optional[str] = None
    enable: bool = False

class PanCloudPatch(BaseModel):
    cookie: Optional[str] = None
    enable: Optional[bool] = None

class PanCloudResponse(BaseModel):
    name: Optional[str]
    cloud_type: CloudType
    cookie: Optional[str]
    enable: bool

# 统一动作响应
class ActionResponse(BaseModel):
    ok: bool
    detail: str

# ---------- helpers ----------
def _doc_to_response(doc: PanCloud) -> Dict[str, Any]:
    return {
        "name": doc.name,
        "cloud_type": doc.cloud_type,
        "cookie": doc.cookie,
        "enable": bool(doc.enable),
    }

def _action_ok(detail: str) -> Dict[str, Any]:
    return {"ok": True, "detail": detail}

# ----------------- endpoints -----------------

@router.post("", response_model=PanCloudResponse, status_code=status.HTTP_201_CREATED)
async def create_pancloud(
    body: PanCloudCreate = Body(...),
    request: Request = None,
    response: Response = None,
):
    """
    创建 PanCloud（使用 name 作为唯一键）。返回 201 Created，body 为资源对象，Location 头指向 /api/v1/panclouds/{name}
    """
    # 如果需要在创建时强制 name + cloud_type 唯一，在此检查并返回 409
    if body.name is not None:
        existing = await PanCloud.find_one({"name": body.name})
        if existing:
            raise HTTPException(status_code=409, detail="resource already exists with same name")

    doc = PanCloud(
        name=body.name,
        cloud_type=body.cloud_type,
        cookie=body.cookie,
        enable=body.enable or False,
    )
    await doc.insert()

    # 生成 Location header（使用 request.url_for 更稳健）
    try:
        location = request.url_for("get_pancloud", name=doc.name)
    except Exception:
        location = f"{router.prefix}/{doc.name}"
    if response is not None:
        response.headers["Location"] = str(location)

    return _doc_to_response(doc)


@router.get("", response_model=List[PanCloudResponse])
async def list_panclouds(
    cloud_type: Optional[CloudType] = Query(None, description="按 cloud_type 过滤"),
    enable: Optional[bool] = Query(None, description="按 enable 过滤"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    列表：支持按 cloud_type / enable 过滤，并支持 offset/limit 分页。
    """
    q = PanCloud.find({})
    if cloud_type is not None:
        q = q.filter(PanCloud.cloud_type == cloud_type)
    if enable is not None:
        q = q.filter(PanCloud.enable == enable)

    docs = await q.skip(offset).limit(limit).to_list()
    return [_doc_to_response(d) for d in docs]




@router.get("/{name}", response_model=PanCloudResponse, name="get_pancloud")
async def get_pancloud(name: str = Path(..., description="PanCloud 唯一 name")):
    doc = await PanCloud.find_one({"name": name})
    if not doc:
        raise HTTPException(status_code=404, detail="not found")
    return _doc_to_response(doc)


# PUT: 完全替换（但 name & cloud_type 不可变）
@router.put("/{name}", response_model=ActionResponse)
async def replace_pancloud(
    name: str = Path(..., description="PanCloud 唯一 name"),
    body: PanCloudReplace = Body(...),
):
    doc = await PanCloud.find_one({"name": name})
    if not doc:
        raise HTTPException(status_code=404, detail="not found")

    # 不允许变更不可变字段
    if (body.name is not None and body.name != doc.name) or (body.cloud_type != doc.cloud_type):
        raise HTTPException(
            status_code=400,
            detail="name and cloud_type are immutable and cannot be changed after creation",
        )

    doc.cookie = body.cookie
    doc.enable = body.enable
    await doc.save()
    return _action_ok("updated")


# PATCH: 部分更新（不允许 name 或 cloud_type 出现在 payload 中）
@router.patch("/{name}", response_model=ActionResponse)
async def patch_pancloud(
    name: str = Path(..., description="PanCloud 唯一 name"),
    body: PanCloudPatch = Body(...),
    request: Request = None,
):
    # 如果你希望严格拒绝客户端发送不可变字段（比如 name/cloud_type）：检查原始 JSON payload 键集合并拒绝包含不可变字段的请求。
    raw = await request.json()
    if "name" in raw or "cloud_type" in raw:
        raise HTTPException(status_code=400, detail="name and cloud_type are immutable and cannot be changed")

    doc = await PanCloud.find_one({"name": name})
    if not doc:
        raise HTTPException(status_code=404, detail="not found")

    if "cookie" in body.__fields_set__:
        doc.cookie = body.cookie
    if body.enable is not None:
        doc.enable = body.enable

    await doc.save()
    return _action_ok("updated")


@router.delete("/{name}", response_model=ActionResponse)
async def delete_pancloud(name: str = Path(..., description="PanCloud 唯一 name")):
    doc = await PanCloud.find_one({"name": name})
    if not doc:
        raise HTTPException(status_code=404, detail="not found")
    await doc.delete()
    return _action_ok("deleted")


# 动作子资源：启用 / 禁用
@router.post("/{name}/enable", response_model=ActionResponse)
async def enable_pancloud(name: str = Path(..., description="PanCloud 唯一 name")):
    doc = await PanCloud.find_one({"name": name})
    if not doc:
        raise HTTPException(status_code=404, detail="not found")
    doc.enable = True
    await doc.save()
    return _action_ok("enabled")


@router.post("/{name}/disable", response_model=ActionResponse)
async def disable_pancloud(name: str = Path(..., description="PanCloud 唯一 name")):
    doc = await PanCloud.find_one({"name": name})
    if not doc:
        raise HTTPException(status_code=404, detail="not found")
    doc.enable = False
    await doc.save()
    return _action_ok("disabled")
