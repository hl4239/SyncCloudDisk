# app/core/task_manager.py
import asyncio
import logging
import uuid
from enum import Enum
from typing import Any, Dict, Optional, List
from collections import deque
from datetime import datetime
import pytz

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class _TaskRecord:
    def __init__(self, id: str, name: Optional[str], params: Dict[str, Any], tz):
        self.id = id
        self.name = name or f"task-{id[:8]}"
        self.params = params or {}
        self.status: TaskStatus = TaskStatus.PENDING
        self.progress: float = 0.0
        # store tz for consistent timestamping
        self.tz = tz
        self.created_at: datetime = datetime.now(self.tz)
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self._log: deque = deque(maxlen=5000)
        self._py_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def append_log(self, line: str):
        # timestamp in configured tz, ISO format with offset
        ts = datetime.now(self.tz).isoformat()
        self._log.append(f"{ts} {line}")

    def get_log(self) -> List[str]:
        return list(self._log)

class TaskManager:
    def __init__(self, default_tz: str = "Asia/Shanghai"):
        self._tasks: Dict[str, _TaskRecord] = {}
        self._lock = asyncio.Lock()
        # store tz object once
        self._tz = pytz.timezone(default_tz)

    async def create_task(self, name: Optional[str], params: Dict[str, Any], coro_fn):
        task_id = uuid.uuid4().hex
        rec = _TaskRecord(task_id, name, params, tz=self._tz)
        async with self._lock:
            self._tasks[task_id] = rec
        py_task = asyncio.create_task(self._wrap_and_run(rec, coro_fn))
        rec._py_task = py_task
        return rec

    async def _wrap_and_run(self, rec: _TaskRecord, coro_fn):
        # get loop for thread-safe callbacks
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        class TaskLogHandler(logging.Handler):
            def __init__(self, rec, loop=None):
                super().__init__()
                self.rec = rec
                self.loop = loop
                # 无色、结构化格式
                fmt = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
                self.setFormatter(logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S"))
                # 确保 handler 不会过滤掉低级别日志
                self.setLevel(logging.DEBUG)

            def emit(self, record: logging.LogRecord) -> None:
                try:
                    msg = self.format(record)
                    if self.loop:
                        try:
                            self.loop.call_soon_threadsafe(self.rec.append_log, msg)
                        except Exception:
                            try:
                                self.rec.append_log(msg)
                            except Exception:
                                pass
                    else:
                        try:
                            self.rec.append_log(msg)
                        except Exception:
                            pass
                except Exception:
                    self.handleError(record)

        handler = TaskLogHandler(rec, loop=loop)

        # decide which loggers to attach to
        attached = []  # list of (logger, original_level)
        capture_names = []
        try:
            capture_names = rec.params.get("capture_loggers") or rec.params.get("_capture_loggers") or []
        except Exception:
            capture_names = []

        try:
            if not capture_names:
                root_logger = logging.getLogger()
                # save original level to restore later
                attached.append((root_logger, root_logger.level))
                # ensure logger level allows debug/info to flow
                try:
                    root_logger.setLevel(min(root_logger.level if root_logger.level else 0, logging.DEBUG))
                except Exception:
                    root_logger.setLevel(logging.DEBUG)
                root_logger.addHandler(handler)
            else:
                for name in capture_names:
                    lg = logging.getLogger(name)
                    attached.append((lg, lg.level))
                    # temporarily lower logger level so INFO/DEBUG aren't filtered
                    try:
                        lg.setLevel(min(lg.level if lg.level else 0, logging.DEBUG))
                    except Exception:
                        lg.setLevel(logging.DEBUG)
                    lg.addHandler(handler)
        except Exception:
            rec.append_log("Failed to attach task log handler")

        # mark running
        async with rec._lock:
            rec.status = TaskStatus.RUNNING
            rec.started_at = datetime.now(rec.tz)
        rec.append_log("Task started (log handler attached)")

        # also emit a test log through root to quickly verify handler captures
        try:
            # write a small test message to the first attached logger
            if attached:
                test_logger = attached[0][0]
                # prefer using module logger name for clear trace
                test_logger.info(f"[task {rec.id}] log handler attached for capture")
        except Exception:
            pass

        try:
            def progress_cb(p: float):
                if loop:
                    # schedule updating progress safely on the loop
                    loop.call_soon_threadsafe(asyncio.create_task, self._set_progress(rec.id, p))
                else:
                    asyncio.create_task(self._set_progress(rec.id, p))

            def log_cb(s: str):
                if loop:
                    loop.call_soon_threadsafe(rec.append_log, s)
                else:
                    rec.append_log(s)

            result = await coro_fn(rec.params, progress_callback=progress_cb, log_callback=log_cb)

            async with rec._lock:
                rec.result = result
                rec.status = TaskStatus.COMPLETED
                rec.progress = 100.0
                rec.finished_at = datetime.now(rec.tz)
            rec.append_log("Task completed successfully")
        except asyncio.CancelledError:
            async with rec._lock:
                rec.status = TaskStatus.CANCELLED
                rec.finished_at = datetime.now(rec.tz)
            rec.append_log("Task was cancelled")
        except Exception as e:
            async with rec._lock:
                rec.status = TaskStatus.FAILED
                rec.error = f"{type(e).__name__}: {e}"
                rec.finished_at = datetime.now(rec.tz)
            rec.append_log(f"Task failed: {type(e).__name__}: {e}")
        finally:
            # cleanup handlers and restore original levels
            try:
                for lg, original_level in attached:
                    try:
                        lg.removeHandler(handler)
                    except Exception:
                        pass
                    try:
                        # restore original level (if was not None)
                        if original_level is not None:
                            lg.setLevel(original_level)
                    except Exception:
                        pass
            except Exception:
                pass

    async def _set_progress(self, task_id: str, p: float):
        rec = await self.get_record(task_id)
        async with rec._lock:
            rec.progress = max(0.0, min(100.0, float(p)))
            rec.append_log(f"Progress updated: {rec.progress}")

    async def list_tasks(self) -> List[_TaskRecord]:
        async with self._lock:
            return list(self._tasks.values())

    async def get_record(self, task_id: str) -> _TaskRecord:
        async with self._lock:
            rec = self._tasks.get(task_id)
            if not rec:
                raise KeyError(task_id)
            return rec

    async def cancel_task(self, task_id: str) -> bool:
        rec = await self.get_record(task_id)
        py_task = rec._py_task
        if py_task and not py_task.done():
            py_task.cancel()
            return True
        return False

    async def cancel_all(self):
        async with self._lock:
            for rec in list(self._tasks.values()):
                if rec._py_task and not rec._py_task.done():
                    rec._py_task.cancel()

# 单例（默认 Asia/Shanghai）
task_manager = TaskManager()
