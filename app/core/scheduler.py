# app/core/scheduler.py
import asyncio
import heapq
import logging
import uuid
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List, Callable, Tuple

from croniter import croniter
import pytz

from app.core.task_registry import registry
from app.core.task_manager import task_manager
from app.database.models import CronJobDoc

logger = logging.getLogger(__name__)

# -------------------------
# 内存堆条目（用于调度优先队列）
# -------------------------
class _HeapEntry:
    __slots__ = ("next_run_ts", "job_id")

    def __init__(self, next_run_ts: float, job_id: str):
        self.next_run_ts = float(next_run_ts)
        self.job_id = job_id

    def __lt__(self, other: "_HeapEntry"):
        return self.next_run_ts < other.next_run_ts


# -------------------------
# CronScheduler（Beanie 持久化，线程安全、无阻塞）
# -------------------------
class CronScheduler:
    def __init__(self, default_tz: str = "Asia/Shanghai"):
        # 默认时区（用于显示/默认计算）
        self.default_tz = default_tz

        # 内存结构（基于 DB 的持久化做恢复）
        self._jobs: Dict[str, CronJobDoc] = {}  # job_id -> CronJobDoc (in-memory copy)
        self._heap: List[_HeapEntry] = []
        self._heap_map: Dict[str, _HeapEntry] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._bg_task: Optional[asyncio.Task] = None
        self._wakeup = asyncio.Event()

    # -------------------------
    # Helper: 统一把各种 datetime 规范到 UTC / epoch
    # -------------------------
    def _to_utc(self, dt: Optional[datetime], assume_tz: Optional[str] = None) -> Optional[datetime]:
        """
        将传入的 datetime 规范化为带有 tzinfo=UTC 的 datetime。
        - 如果 dt 为 None -> 返回 None
        - 如果 dt.tzinfo is None -> 根据 assume_tz（或 self.default_tz）进行 localize
        - 返回值 guaranteed tz-aware（UTC）
        """
        if dt is None:
            return None
        if dt.tzinfo is None:
            tzname = assume_tz or self.default_tz
            try:
                tz = pytz.timezone(tzname)
                dt = tz.localize(dt)
            except Exception:
                # 兜底假设 UTC
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _dt_to_ts(self, dt: datetime) -> float:
        """
        把任意 tz-aware/naive datetime 转成 UTC epoch 秒（float）。
        """
        return self._to_utc(dt).timestamp()

    def _doc_next_ts(self, doc: CronJobDoc) -> float:
        """
        从 CronJobDoc 安全地获取 next_run_at 的 UTC epoch。如果缺失，返回当前时间。
        注意：CronJobDoc 可能已经被 model_validator 转换成默认时区（比如 Asia/Shanghai）。
        """
        nxt = getattr(doc, "next_run_at", None)
        if not nxt:
            return time.time()
        try:
            return self._dt_to_ts(nxt)
        except Exception:
            # 最后兜底：尝试直接用 timestamp（若 tz-aware 则有效）
            try:
                return nxt.timestamp()
            except Exception:
                return time.time()

    # -------------------------
    # 公共 API（注意：这些方法不会在持锁期间 await DB I/O）
    # -------------------------
    async def start(self):
        """
        启动调度器（安全，不会死锁）。
        - 在短临界区内设置 self._running=True 避免重复启动；
        - 释放锁后加载 DB（_load_from_db 做必要的 DB I/O，但不会在持锁时 await）；
        - 最后在短临界区内创建后台循环任务。
        """
        async with self._lock:
            if self._running:
                logger.debug("CronScheduler.start called but already running")
                return
            self._running = True

        try:
            await self._load_from_db()
        except Exception:
            # 加载失败，回滚 running 标记并重抛
            async with self._lock:
                self._running = False
            logger.exception("Failed to load cron jobs from DB during scheduler.start()")
            raise

        async with self._lock:
            if self._bg_task is None or self._bg_task.done():
                self._bg_task = asyncio.create_task(self._run_loop())
        logger.info("CronScheduler started (Beanie persistence)")

    async def stop(self, wait_running_tasks: bool = False):
        """
        停止调度器。不会直接取消已经提交给 task_manager 的任务（task_manager 负责它们）。
        """
        async with self._lock:
            if not self._running:
                return
            self._running = False
            # 唤醒等待，保证 _run_loop 能尽快看到 _running=False 并退出
            self._wakeup.set()
            bg = self._bg_task
            self._bg_task = None

        if bg:
            try:
                # 等待 bg 退出
                await bg
            except Exception:
                logger.exception("Error stopping scheduler bg task")

        if wait_running_tasks:
            logger.info("CronScheduler stopped (wait_running_tasks requested)")

    async def add_job(self, task_name: str, cron: str, params: Optional[Dict[str, Any]] = None,
                      tz: Optional[str] = None, job_id: Optional[str] = None) -> str:
        """
        添加 job：
         - 先计算 next_run（同步 CPU），
         - 在外部创建并保存 CronJobDoc（await），
         - 然后在短临界区内把 doc 加入内存 heap（不 await）。
        默认 tz 使用 self.default_tz（Asia/Shanghai）。
        """
        tz = tz or self.default_tz
        job_id = job_id or uuid.uuid4().hex
        # 先计算下一次触发时间（同步）
        next_dt = self._compute_next(cron, tz)
        doc = CronJobDoc(
            job_id=job_id,
            task_name=task_name,
            cron=cron,
            params=params or {},
            tz=tz,
            enabled=True,
            created_at=datetime.now(timezone.utc),
            # 仍然以 UTC 存储 DB，保持一致性 —— model 可能在保存/读取时转换时区，
            # 我们在内存层使用 helper 进行统一处理。
            next_run_at=next_dt.astimezone(timezone.utc),
        )

        # DB 插入（在锁外 await）
        await doc.insert()

        # 将插入结果写入内存（短临界区，不 await）
        he = _HeapEntry(next_run_ts=self._doc_next_ts(doc), job_id=job_id)
        async with self._lock:
            self._jobs[job_id] = doc
            heapq.heappush(self._heap, he)
            self._heap_map[job_id] = he
            self._wakeup.set()

        # log 时把时间以默认时区显示（可读）
        try:
            # doc.next_run_at 可能已经被 model 转换到默认时区（如 Asia/Shanghai），
            # 这里统一把时间显示到 self.default_tz 供人类阅读。
            next_local = self._to_utc(doc.next_run_at).astimezone(pytz.timezone(self.default_tz))
        except Exception:
            # 兜底
            next_local = doc.next_run_at
        logger.info("Added cron job %s -> %s (next %s %s)", job_id, task_name, next_local, f"({self.default_tz})")
        return job_id

    async def remove_job(self, job_id: str) -> bool:
        """
        删除 job：
         - 先在 DB 中查并删除（await）；
         - 然后在短临界区内移除内存结构（不 await）。
        """
        found = await CronJobDoc.find_one(CronJobDoc.job_id == job_id)
        if not found:
            return False

        await found.delete()

        async with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
            if job_id in self._heap_map:
                del self._heap_map[job_id]
            # heap 中 stale entry lazy-delete
            self._wakeup.set()

        logger.info("Removed cron job %s", job_id)
        return True

    async def list_jobs(self) -> List[Dict[str, Any]]:
        """
        返回 DB 中所有 job（以 dict 形式），并附带以默认时区（self.default_tz）表示的时间字段用于展示。
        DB I/O 在外部完成，不持锁。
        """
        docs = await CronJobDoc.find_all().to_list()
        results: List[Dict[str, Any]] = []
        tz_obj = pytz.timezone(self.default_tz)
        for d in docs:
            data = d.model_dump()
            # 在返回结果中附加本地化时间字段（字符串 ISO 格式）
            try:
                data["created_at_local"] = d.created_at.astimezone(tz_obj).isoformat() if d.created_at else None
            except Exception:
                data["created_at_local"] = None
            try:
                data["next_run_at_local"] = d.next_run_at.astimezone(tz_obj).isoformat() if d.next_run_at else None
            except Exception:
                data["next_run_at_local"] = None
            try:
                data["last_run_at_local"] = d.last_run_at.astimezone(tz_obj).isoformat() if getattr(d, "last_run_at", None) else None
            except Exception:
                data["last_run_at_local"] = None
            # 原始字段仍保留（如果调用方需要）
            results.append(data)
        return results

    async def run_once(self, job_id: str) -> bool:
        """
        立即触发一次（不改变计划）。只在短临界区检查内存状态，然后异步派发（不 await）。
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job or not job.enabled:
                return False
            # 非阻塞地创建后台 dispatch（不在持锁时 await）
            asyncio.create_task(self._safe_dispatch_and_reschedule(job))
            return True

    async def enable_job(self, job_id: str) -> bool:
        """
        启用 job：先读取 DB，计算 next_run 并保存（await），再把结果更新到内存（短临界区）。
        """
        doc = await CronJobDoc.find_one(CronJobDoc.job_id == job_id)
        if not doc:
            return False

        doc.enabled = True
        # 重新计算下一次（使用 doc.tz 或默认）
        next_dt = self._compute_next(doc.cron, doc.tz or self.default_tz)
        # 统一保存为 UTC（model 验证器会在保存/读出时做它的转换，我们在内存端用 helper 处理）
        doc.next_run_at = next_dt.astimezone(timezone.utc)
        await doc.save()

        he = _HeapEntry(next_run_ts=self._dt_to_ts(next_dt), job_id=job_id)
        async with self._lock:
            self._jobs[job_id] = doc
            heapq.heappush(self._heap, he)
            self._heap_map[job_id] = he
            self._wakeup.set()
        return True

    async def disable_job(self, job_id: str) -> bool:
        """
        禁用 job：先在 DB 保存 enabled=False（await），然后在短临界区更新内存结构（不 await）。
        """
        doc = await CronJobDoc.find_one(CronJobDoc.job_id == job_id)
        if not doc:
            return False

        doc.enabled = False
        await doc.save()

        async with self._lock:
            if job_id in self._heap_map:
                del self._heap_map[job_id]
            # 保留 doc 在 self._jobs 中以便查询
            self._jobs[job_id] = doc
            self._wakeup.set()
        return True

    async def update_job(self, job_id: str, *, cron: Optional[str] = None,
                         params: Optional[Dict[str, Any]] = None, tz: Optional[str] = None,
                         enabled: Optional[bool] = None) -> bool:
        """
        原地更新 job（不会删除重建），策略：
         - 读取 DB（await），修改字段并根据需要计算 next_run（同步计算），保存（await）；
         - 在短临界区更新内存 heap（不 await）。
        """
        doc = await CronJobDoc.find_one(CronJobDoc.job_id == job_id)
        if not doc:
            return False

        # 决定是否需要重新计算 next_run
        need_recompute = False
        if cron is not None and cron != doc.cron:
            doc.cron = cron
            need_recompute = True
        if tz is not None and tz != doc.tz:
            doc.tz = tz
            need_recompute = True
        if params is not None:
            doc.params = params
        if enabled is not None:
            doc.enabled = bool(enabled)

        if need_recompute or doc.next_run_at is None:
            next_dt = self._compute_next(doc.cron, doc.tz or self.default_tz)
            # 保存为 UTC（model 将在持久化/读取时转换）
            doc.next_run_at = next_dt.astimezone(timezone.utc)

        # 保存到 DB（外部 await）
        await doc.save()

        # 更新内存（短临界区）
        async with self._lock:
            # 更新 jobs map
            self._jobs[job_id] = doc
            # 更新 heap entry： push 新条目，lazy 删除旧的（但标记 heap_map 为最新）
            if doc.next_run_at:
                he = _HeapEntry(next_run_ts=self._doc_next_ts(doc), job_id=job_id)
                heapq.heappush(self._heap, he)
                self._heap_map[job_id] = he
            # 如果被禁用，移除 heap_map 关联
            if not doc.enabled and job_id in self._heap_map:
                del self._heap_map[job_id]
            self._wakeup.set()

        return True

    # -------------------------
    # 调度内部循环与 dispatch（核心不持锁做 I/O）
    # -------------------------
    async def _run_loop(self):
        logger.debug("CronScheduler loop started")
        try:
            while self._running:
                # 1) 从堆读取最早的任务并计算等待时间（短临界区）
                async with self._lock:
                    # lazy 清理 heap：移除指向已删除 job 的条目，或被覆盖（非最新）的 stale 条目
                    while self._heap and (
                        self._heap[0].job_id not in self._jobs
                        or self._heap_map.get(self._heap[0].job_id) is not self._heap[0]
                    ):
                        heapq.heappop(self._heap)

                    if not self._heap:
                        # 如果没有任务，释放锁并等待唤醒
                        self._wakeup.clear()
                        waiter = self._wakeup.wait()
                        # 在锁外等待（不会阻塞其它 API）
                        pass
                    else:
                        next_entry = self._heap[0]
                        # 再次判断：如果堆顶已经不是最新 entry（可能在上面循环后被外部更新），跳过
                        if self._heap_map.get(next_entry.job_id) is not next_entry:
                            # stale entry（被替换）——弹出并循环
                            heapq.heappop(self._heap)
                            waiter = None
                        else:
                            job_doc = self._jobs.get(next_entry.job_id)
                            if not job_doc or not job_doc.enabled:
                                # 弹出并在 map 中只在匹配时删除（避免误删新 entry）
                                heapq.heappop(self._heap)
                                if self._heap_map.get(next_entry.job_id) is next_entry:
                                    del self._heap_map[next_entry.job_id]
                                waiter = None
                            else:
                                next_ts = next_entry.next_run_ts
                                now_ts = time.time()
                                wait_seconds = max(0.0, next_ts - now_ts)
                                self._wakeup.clear()
                                waiter = self._wakeup.wait()
                                # will wait for either timeout or wakeup

                # 2) 在锁外执行等待操作（避免阻塞其他 API）
                if 'wait_seconds' in locals() and waiter is not None:
                    try:
                        # 等待到期或 wakeup
                        await asyncio.wait_for(waiter, timeout=wait_seconds)
                        # 若被唤醒则 loop 回到开头
                        continue
                    except asyncio.TimeoutError:
                        # timeout -> 到点，继续弹出到期任务
                        pass
                    finally:
                        # 清理本次循环里使用的局部变量，避免误用
                        wait_seconds = None
                else:
                    # 没有任务 -> 等待唤醒
                    if waiter is not None:
                        await waiter
                    # loop
                    continue

                # 3) 到点：弹出所有到期的任务（在短临界区内，只做内存操作）
                due_docs: List[CronJobDoc] = []
                async with self._lock:
                    now_ts = time.time()
                    while self._heap and self._heap[0].next_run_ts <= now_ts + 1e-6:
                        he = heapq.heappop(self._heap)
                        # 跳过不是最新的 stale entry
                        if self._heap_map.get(he.job_id) is not he:
                            continue
                        doc = self._jobs.get(he.job_id)
                        if not doc or not doc.enabled:
                            # 仅在 heap_map 指向当前 entry 时才删除 map
                            if self._heap_map.get(he.job_id) is he:
                                del self._heap_map[he.job_id]
                            continue
                        due_docs.append(doc)
                        # 仅在 heap_map 指向当前 entry 时才删除 map
                        if self._heap_map.get(he.job_id) is he:
                            del self._heap_map[he.job_id]

                # 4) 在锁外并发调度所有到期任务（避免持锁）
                for doc in due_docs:
                    asyncio.create_task(self._safe_dispatch_and_reschedule(doc))

        except asyncio.CancelledError:
            logger.info("CronScheduler loop cancelled")
        except Exception:
            logger.exception("Exception in CronScheduler loop")
        finally:
            logger.debug("CronScheduler loop exited")

    async def _safe_dispatch_and_reschedule(self, doc: CronJobDoc):
        """
        先 dispatch（await task_manager.create_task），dispatch 完后再计算并保存 next_run，并在短临界区内更新内存结构。
        所有 DB I/O 均在不持锁时进行。
        """
        try:
            await self._dispatch_job(doc)
        except Exception:
            logger.exception("Error dispatching job %s", doc.job_id)
        finally:
            try:
                # 从 DB 重新读取最新 doc（await）
                fresh = await CronJobDoc.find_one(CronJobDoc.job_id == doc.job_id)
                if not fresh or not fresh.enabled:
                    return
                # 计算下次（同步，使用 doc.tz 或默认）
                next_dt = self._compute_next(fresh.cron, fresh.tz or self.default_tz)
                fresh.last_run_at = datetime.now(timezone.utc)
                fresh.next_run_at = next_dt.astimezone(timezone.utc)
                # 保存到 DB（await）
                await fresh.save()
                # 在短临界区更新内存结构（不 await），使用 helper 得到正确的 UTC timestamp
                he = _HeapEntry(next_run_ts=self._dt_to_ts(next_dt), job_id=fresh.job_id)
                async with self._lock:
                    self._jobs[fresh.job_id] = fresh
                    heapq.heappush(self._heap, he)
                    self._heap_map[fresh.job_id] = he
                    self._wakeup.set()
            except Exception:
                logger.exception("Failed to reschedule job %s", getattr(doc, "job_id", "<unknown>"))

    async def _dispatch_job(self, doc: CronJobDoc):
        """
        把 schedule 转为 task_manager 的任务。所有校验/调用都在这里（DB I/O 已在外面）。
        """
        logger.info("Dispatching scheduled job %s -> %s", doc.job_id, doc.task_name)

        async def coro_fn(params: Dict[str, Any], progress_callback: Callable[[float], None], log_callback: Callable[[str], None]):
            try:
                entry = registry.get(doc.task_name)
            except KeyError:
                msg = f"task '{doc.task_name}' not found in registry"
                logger.error(msg)
                log_callback(msg)
                raise

            params_to_pass = params or {}
            model_cls = getattr(entry, "params_model", None)
            if model_cls:
                try:
                    validated = model_cls.model_validate(params_to_pass)
                    params_to_pass = validated.model_dump()
                except Exception as e:
                    log_callback(f"params validation error for scheduled job {doc.job_id}: {e}")
                    raise

            return await entry.fn(params_to_pass, progress_callback, log_callback)

        # create_task 是 awaitable（会创建任务记录并在后台执行）
        try:
            await task_manager.create_task(name=doc.task_name, params=doc.params or {}, coro_fn=coro_fn)
            logger.info("Scheduled job %s dispatched to task_manager", doc.job_id)
        except Exception:
            logger.exception("Failed to create task for scheduled job %s", doc.job_id)
            raise

    # -------------------------
    # 从 DB 恢复（无阻塞版）
    # -------------------------
    async def _load_from_db(self):
        """
        从 DB 恢复 jobs 到内存（避免在持锁期间做 DB I/O）：
          1) 一次性从 DB 读取全部文档（await）
          2) 在内存中计算需要更新 next_run_at 的文档（纯同步）
          3) 在锁外对需要保存的文档执行 await save()
          4) 在短临界区把所有成功的文档载入 self._jobs 与 heap（不 await）
        """
        # 1) 从 DB 读取所有文档（await）
        docs = await CronJobDoc.find_all().to_list()

        # 2) 计算需要持久化更新的文档（同步）
        docs_to_save: List[CronJobDoc] = []
        prepared: List[Tuple[CronJobDoc, float]] = []
        now_utc = datetime.now(timezone.utc)

        for d in docs:
            try:
                if not d.next_run_at:
                    next_dt = self._compute_next(d.cron, d.tz or self.default_tz)
                    d.next_run_at = next_dt.astimezone(timezone.utc)
                    docs_to_save.append(d)
                else:
                    # 确保 tz-aware（model 可能已经把时间变为默认时区）
                    if d.next_run_at.tzinfo is None:
                        d.next_run_at = d.next_run_at.replace(tzinfo=timezone.utc)
                # 使用 helper 获取正确的 epoch（无论 doc.next_run_at 是哪种时区）
                prepared.append((d, self._doc_next_ts(d)))
            except Exception:
                logger.exception("Failed computing next for job %s; skipping", getattr(d, "job_id", "<unknown>"))
                # skip
                continue

        # 3) 在锁外保存需要更新的文档（await）
        if docs_to_save:
            for d in docs_to_save:
                try:
                    await d.save()
                except Exception:
                    logger.exception("Failed to save next_run_at for job %s", getattr(d, "job_id", "<unknown>"))
                    # skip failing doc from prepared list
                    prepared = [p for p in prepared if p[0].job_id != d.job_id]

        # 4) 在短临界区内把成功准备好的文档载入内存（不 await）
        async with self._lock:
            self._jobs.clear()
            self._heap.clear()
            self._heap_map.clear()
            for d, next_ts in prepared:
                try:
                    self._jobs[d.job_id] = d
                    he = _HeapEntry(next_run_ts=next_ts, job_id=d.job_id)
                    heapq.heappush(self._heap, he)
                    self._heap_map[d.job_id] = he
                except Exception:
                    logger.exception("Failed to push job %s into heap", getattr(d, "job_id", "<unknown>"))
                    continue

        logger.info("Loaded %d cron jobs from DB", len(self._jobs))

    # -------------------------
    # Cron / tz helper（同步）
    # -------------------------
    def _compute_next(self, cron_expr: str, tz_name: Optional[str] = None, base: Optional[datetime] = None) -> datetime:
        """
        计算下次触发时间，返回带有 tz 的 datetime。
        tz_name 优先使用传入值，否则使用 self.default_tz。
        """
        tz_name = tz_name or self.default_tz
        tz = pytz.timezone(tz_name)
        if base is None:
            base = datetime.now(tz)
        else:
            if base.tzinfo is None:
                base = tz.localize(base)
            else:
                base = base.astimezone(tz)
        ci = croniter(cron_expr, base)
        nxt = ci.get_next(datetime)
        if nxt.tzinfo is None:
            nxt = tz.localize(nxt)
        return nxt
    async def get_status(self, limit: int = 5) -> Dict[str, Any]:
        """
        返回调度器内存中当前状态快照（不会进行 DB I/O）。
        返回 dict 结构，字段与 API 的 SchedulerStatusResponse 一致：
          {
            "running": bool,
            "jobs_count": int,
            "heap_size": int,
            "bg_task_active": bool,
            "next_run": Optional[{"job_id","task_name","next_run_at","next_run_at_local"}],
            "upcoming": [ ... same items ... ],
            "tz": str
          }
        注意：
        - 该方法在内部使用 self._lock 保证一致性快照（不会进行 await 的 DB I/O）。
        - 只将 heap_map 中仍然指向该 entry 的视为有效（与调度循环一致）。
        """
        from datetime import datetime, timezone  # local import to avoid circulars if necessary
        # prepare
        upcoming_list = []
        next_run_info = None
        tz_name = self.default_tz or "UTC"
        try:
            tz_obj = pytz.timezone(tz_name)
        except Exception:
            tz_obj = pytz.timezone("UTC")
            tz_name = "UTC"

        async with self._lock:
            running = bool(self._running)
            jobs_count = len(self._jobs)
            heap_size = len(self._heap)
            bg_task_active = bool(self._bg_task and not self._bg_task.done())

            # collect valid entries: those whose heap_map still points to the same entry, and job exists+enabled
            valid_entries = []
            for he in list(self._heap):
                mapped = self._heap_map.get(he.job_id)
                if mapped is not he:
                    # stale or replaced
                    continue
                job_doc = self._jobs.get(he.job_id)
                if not job_doc or not getattr(job_doc, "enabled", False):
                    continue
                valid_entries.append((he.next_run_ts, he.job_id, getattr(job_doc, "task_name", None)))

            # sort and slice
            valid_entries.sort(key=lambda x: x[0])
            sliced = valid_entries[:max(0, int(limit))]

            for ts, job_id, task_name in sliced:
                dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
                dt_local = dt_utc.astimezone(tz_obj)
                item = {
                    "job_id": job_id,
                    "task_name": task_name,
                    "next_run_at": dt_utc,
                    "next_run_at_local": dt_local,
                }
                upcoming_list.append(item)

            if upcoming_list:
                next_run_info = upcoming_list[0]

        return {
            "running": running,
            "jobs_count": jobs_count,
            "heap_size": heap_size,
            "bg_task_active": bg_task_active,
            "next_run": next_run_info,
            "upcoming": upcoming_list,
            "tz": tz_name,
        }

# 单例（默认时区 Asia/Shanghai）
scheduler = CronScheduler()
