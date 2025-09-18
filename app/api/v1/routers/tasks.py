# app/api/v1/routers/tasks.py
import logging

from fastapi import APIRouter, HTTPException, Body, Path, Query
from pydantic import BaseModel
from typing import Any, Dict, Optional, List

from app.core.logging_config import setup_logging
from app.core.task_registry import registry
from app.core.task_manager import task_manager, TaskStatus  # 之前实现的 task_manager
import app.flow.tasks
router = APIRouter()
logger=logging.getLogger(name=__name__)
class GenericTaskCreate(BaseModel):
    name: str  # 要执行的任务名（在 registry 中注册）
    params: Optional[Dict[str, Any]] = {}
# ---------- 启动任务（你已有的） ----------
@router.post("", response_model=dict)
async def start_task(body: GenericTaskCreate = Body(...)):
    # 查找任务
    try:
        logger.debug(f"start task {body.name}")
        entry = registry.get(body.name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"task '{body.name}' not found")

    # 如果任务提供了 params_model，则先用该 model 校验 params
    params_obj = body.params or {}
    if entry.params_model:
        try:
            # 将 dict 转为 model（会校验类型、默认值等）
            model_instance = entry.params_model(**params_obj)
            params_obj = model_instance.dict()  # 转为普通 dict 传给任务
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"params validation error: {e}")

    # 创建任务：把 entry.fn 作为 coro_fn 传入 task_manager
    rec = await task_manager.create_task(body.name, params_obj, entry.fn)
    return {
        "id": rec.id,
        "name": rec.name,
        "status": rec.status,
        "created_at": rec.created_at.isoformat() if rec.created_at else None
    }

# ---------- 辅助转换函数 ----------
def _rec_to_summary(rec) -> Dict[str, Any]:
    return {
        "id": rec.id,
        "name": rec.name,
        "status": rec.status,
        "progress": float(rec.progress or 0.0),
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
        "started_at": rec.started_at.isoformat() if rec.started_at else None,
        "finished_at": rec.finished_at.isoformat() if rec.finished_at else None,
    }

def _rec_to_detail(rec) -> Dict[str, Any]:
    return {
        "id": rec.id,
        "name": rec.name,
        "status": rec.status,
        "progress": float(rec.progress or 0.0),
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
        "started_at": rec.started_at.isoformat() if rec.started_at else None,
        "finished_at": rec.finished_at.isoformat() if rec.finished_at else None,
        "params": rec.params or {},
        "result": rec.result,
        "error": rec.error,
        "log": rec.get_log(),
    }

# ---------- 列表（支持过滤/分页） ----------
@router.get("", response_model=List[Dict[str, Any]])
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="按状态过滤, e.g. RUNNING"),
    name: Optional[str] = Query(None, description="按任务 name 过滤（精确匹配）"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    列出任务，支持按 status/name 过滤并做分页（offset/limit）。
    默认按创建时间降序返回。
    """
    recs = await task_manager.list_tasks()  # 返回 _TaskRecord 列表

    # 过滤
    if status is not None:
        recs = [r for r in recs if r.status == status]
    if name:
        recs = [r for r in recs if r.name == name]

    # 排序（创建时间降序）
    recs.sort(key=lambda r: r.created_at or 0, reverse=True)

    # 分页
    recs = recs[offset: offset + limit]

    return [_rec_to_summary(r) for r in recs]

# ---------- 详情 ----------
@router.get("/{task_id}", response_model=Dict[str, Any])
async def get_task_detail(task_id: str = Path(..., description="任务 ID")):
    """
    返回任务详情：包括 params、progress、result、error、log（全部）
    """
    try:
        rec = await task_manager.get_record(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")
    return _rec_to_detail(rec)

# ---------- 日志（支持 tail） ----------
@router.get("/{task_id}/log", response_model=List[str])
async def get_task_log(
    task_id: str = Path(..., description="任务 ID"),
    tail: Optional[int] = Query(None, description="仅返回最后 N 行日志（可选）"),
):
    """
    返回任务的全部日志（按时间升序）。
    使用 tail 参数可以只返回末尾 N 行，减少传输量。
    """
    try:
        rec = await task_manager.get_record(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")

    logs = rec.get_log()
    if tail is not None:
        try:
            n = int(tail)
            if n < 0:
                raise ValueError
        except Exception:
            raise HTTPException(status_code=400, detail="tail must be a non-negative integer")
        if n == 0:
            return []
        return logs[-n:]
    return logs

# ---------- 取消 ----------
@router.delete("/{task_id}", response_model=Dict[str, bool])
async def cancel_task(task_id: str = Path(..., description="任务 ID")):
    """
    请求取消任务：如果任务仍在运行，会给 asyncio.Task 发 cancel 信号。
    返回 {"cancel_requested": true/false}
    """
    try:
        ok = await task_manager.cancel_task(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")
    return {"cancel_requested": bool(ok)}
