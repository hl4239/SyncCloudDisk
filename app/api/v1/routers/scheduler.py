# app/api/scheduler.py
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel as PydanticBaseModel, Field
from datetime import datetime, timezone

from app.core.scheduler import scheduler  # 单例 CronScheduler
from app.database.models import CronJobDoc

router = APIRouter()
logger = logging.getLogger(__name__)

# -------------------------
# Request / Response models
# -------------------------
class JobCreateRequest(PydanticBaseModel):
    task_name: str = Field(..., description="在 registry 中注册的任务名")
    cron: str = Field(..., description="cron 表达式（5 或 6 字段支持）")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="传入任务的参数 dict")
    tz: str = Field("UTC", description="时区，例如 'UTC' 或 'Asia/Shanghai'")
    job_id: Optional[str] = Field(None, description="可选的外部指定 job_id（不指定自动生成）")


class JobUpdateRequest(PydanticBaseModel):
    cron: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    tz: Optional[str] = None
    enabled: Optional[bool] = None


class JobResponse(PydanticBaseModel):
    job_id: str
    task_name: str
    cron: str
    params: Dict[str, Any]
    tz: str
    enabled: bool
    created_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None


class SimpleResponse(PydanticBaseModel):
    ok: bool
    detail: Optional[str] = None


# -------------------------
# Helper
# -------------------------
async def _fetch_doc_by_job_id(job_id: str) -> CronJobDoc:
    doc = await CronJobDoc.find_one(CronJobDoc.job_id == job_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"job {job_id} not found")
    return doc


def _doc_to_response_dict(doc: CronJobDoc) -> Dict[str, Any]:
    # CronJobDoc.model_dump() 返回 pydantic-friendly dict
    data = doc.model_dump()
    # Ensure datetimes are timezone-aware / isoformat will be done by FastAPI automatically
    return {
        "job_id": data.get("job_id"),
        "task_name": data.get("task_name"),
        "cron": data.get("cron"),
        "params": data.get("params") or {},
        "tz": data.get("tz"),
        "enabled": bool(data.get("enabled", True)),
        "created_at": data.get("created_at"),
        "last_run_at": data.get("last_run_at"),
        "next_run_at": data.get("next_run_at"),
    }


# -------------------------
# Endpoints
# -------------------------
@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs():
    """
    列出所有调度任务（来自 DB），返回完整字段。
    """
    docs = await CronJobDoc.find_all().to_list()
    return [_doc_to_response_dict(d) for d in docs]


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(req: JobCreateRequest):
    """
    新增一个定时任务。
    - 验证 cron（会通过 scheduler._compute_next 计算下一次运行时间）
    - 持久化到 DB（由 scheduler.add_job 完成）并返回 job 信息
    """
    # 验证 cron 与 tz 通过 scheduler 计算下一次触发（会抛 ValueError 如果无效）
    try:
        _ = scheduler._compute_next(req.cron, req.tz)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid cron/tz: {e}")

    try:
        job_id = await scheduler.add_job(task_name=req.task_name, cron=req.cron, params=req.params or {},
                                         tz=req.tz, job_id=req.job_id)
    except Exception as e:
        logger.exception("failed to add cron job")
        raise HTTPException(status_code=500, detail=str(e))

    # 读取并返回刚插入的 doc
    doc = await _fetch_doc_by_job_id(job_id)
    return _doc_to_response_dict(doc)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    获取单个任务的详情（DB 中的记录）。
    """
    doc = await _fetch_doc_by_job_id(job_id)
    return _doc_to_response_dict(doc)


@router.delete("/jobs/{job_id}", response_model=SimpleResponse)
async def delete_job(job_id: str):
    """
    删除 job（从 DB 中删除并从内存中移除）。
    """
    ok = await scheduler.remove_job(job_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"job {job_id} not found")
    return SimpleResponse(ok=True, detail="deleted")


@router.patch("/jobs/{job_id}", response_model=JobResponse)
async def update_job(job_id: str, req: JobUpdateRequest):
    """
    更新 job（支持更新 cron / params / tz / enabled）。
    实现策略：读取原始 doc -> 删除原有 job -> 使用相同 job_id 重新创建（保留 job_id）。
    这种方式简单且能正确重建调度队列和 next_run_at。
    """
    # 读取原始
    doc = await CronJobDoc.find_one(CronJobDoc.job_id == job_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"job {job_id} not found")

    # 构造新的值（未提供字段保留原值）
    new_cron = req.cron if req.cron is not None else doc.cron
    new_params = req.params if req.params is not None else (doc.params or {})
    new_tz = req.tz if req.tz is not None else doc.tz
    new_enabled = req.enabled if req.enabled is not None else bool(doc.enabled)

    # 验证 cron/tz
    try:
        _ = scheduler._compute_next(new_cron, new_tz)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid cron/tz: {e}")

    # 删除旧的并用相同 job_id 新建（保持接口简单、避免直接操作 scheduler 内部结构）
    removed = await scheduler.remove_job(job_id)
    if not removed:
        # 如果未找到可能 race condition，仍尝试继续以覆盖 DB
        logger.warning("update_job: remove_job reported False for %s, attempting to recreate", job_id)

    try:
        new_job_id = await scheduler.add_job(task_name=req.params.get("task_name", doc.task_name) if isinstance(req.params, dict) and req.params.get("task_name") else doc.task_name,
                                            cron=new_cron, params=new_params, tz=new_tz, job_id=job_id)
    except Exception as e:
        logger.exception("failed to recreate job during update")
        raise HTTPException(status_code=500, detail=str(e))

    # 如果需要禁用，则调用 disable_job
    if not new_enabled:
        await scheduler.disable_job(job_id)
    else:
        # ensure enabled
        await scheduler.enable_job(job_id)

    new_doc = await _fetch_doc_by_job_id(new_job_id)
    return _doc_to_response_dict(new_doc)


@router.post("/jobs/{job_id}/enable", response_model=SimpleResponse)
async def enable_job(job_id: str):
    ok = await scheduler.enable_job(job_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"job {job_id} not found")
    return SimpleResponse(ok=True, detail="enabled")


@router.post("/jobs/{job_id}/disable", response_model=SimpleResponse)
async def disable_job(job_id: str):
    ok = await scheduler.disable_job(job_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"job {job_id} not found")
    return SimpleResponse(ok=True, detail="disabled")


@router.post("/jobs/{job_id}/run", response_model=SimpleResponse)
async def run_job_once(job_id: str):
    """
    立即触发一次任务（不改变计划的下一次触发时间）。
    """
    ok = await scheduler.run_once(job_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"job {job_id} not found or disabled")
    return SimpleResponse(ok=True, detail="dispatched")


@router.post("/start", response_model=SimpleResponse)
async def start_scheduler():
    """
    启动调度器（恢复 DB 中已有任务并开始循环）。
    如果已经启动则无操作。
    """
    await scheduler.start()
    return SimpleResponse(ok=True, detail="scheduler started")


@router.post("/stop", response_model=SimpleResponse)
async def stop_scheduler(wait_running: bool = True):
    """
    停止调度器后台循环；可选等待正在运行任务完成（默认 True）。
    """
    await scheduler.stop(wait_running_tasks=wait_running)
    return SimpleResponse(ok=True, detail="scheduler stopped")
