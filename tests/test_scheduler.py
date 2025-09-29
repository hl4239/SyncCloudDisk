# tests/test_scheduler_no_dup.py
import asyncio
from datetime import datetime, timezone, timedelta
import pytest
import time

# 需要 pytest-asyncio
pytest_plugins = ("pytest_asyncio",)

# 导入被测模块（确保 PYTHONPATH 包含项目根目录）
import importlib
import app.core.scheduler as scheduler_mod

# 便捷访问单例
sched = scheduler_mod.scheduler

# ----------------------------
# Fake DB model: CronJobDoc
# ----------------------------
class FakeQueryAll:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self):
        # emulate beanie's to_list
        return list(self._docs)

class FakeCronJobDoc:
    """
    Minimal fake for CronJobDoc used by scheduler:
    - class storage _store: job_id -> instance
    - async classmethods: find_one, find_all
    - instance async methods: insert, save, delete
    - attributes used by scheduler: job_id, cron, params, tz, enabled, created_at, next_run_at, last_run_at
    """
    _store = {}

    def __init__(self, job_id, task_name, cron, params=None, tz="Asia/Shanghai",
                 enabled=True, created_at=None, next_run_at=None):
        self.job_id = job_id
        self.task_name = task_name
        self.cron = cron
        self.params = params or {}
        self.tz = tz
        self.enabled = enabled
        self.created_at = created_at or datetime.now(timezone.utc)
        self.next_run_at = next_run_at
        self.last_run_at = None

    # persistence-like ops
    async def insert(self):
        FakeCronJobDoc._store[self.job_id] = self
        return self

    async def save(self):
        FakeCronJobDoc._store[self.job_id] = self
        return self

    async def delete(self):
        FakeCronJobDoc._store.pop(self.job_id, None)
        return None

    # class query ops
    @classmethod
    async def find_one(cls, cond):
        """
        The scheduler calls:
            await CronJobDoc.find_one(CronJobDoc.job_id == job_id)
        We'll support either being called with a simple lambda or with a tuple-like condition.
        But easiest: the tests will call with (CronJobDoc.job_id == job_id) replaced by a simple helper,
        so here we accept either a callable or a string comparison object.
        """
        # If cond is a callable take it as a predicate
        if callable(cond):
            for d in cls._store.values():
                try:
                    if cond(d):
                        return d
                except Exception:
                    continue
            return None

        # If cond is of form ("job_id", "==", job_id) or a string, try to handle common cases.
        # For robustness we'll allow cond to be "job_id==<id>" or job_id string.
        try:
            # cond might be a simple object with right-hand value as attribute 'arg'
            # But to keep tests simple we will call find_one with a lambda in monkeypatch below.
            return None
        except Exception:
            return None

    @classmethod
    def find_all(cls):
        # return an object supporting to_list()
        return FakeQueryAll(list(cls._store.values()))

    def model_dump(self):
        # used by list_jobs to get a dict
        return {
            "job_id": self.job_id,
            "task_name": self.task_name,
            "cron": self.cron,
            "params": self.params,
            "tz": self.tz,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "next_run_at": self.next_run_at,
            "last_run_at": self.last_run_at,
        }

# ----------------------------
# Fixtures
# ----------------------------
@pytest.fixture(autouse=True)
def reset_fake_store():
    # runs before each test
    FakeCronJobDoc._store.clear()
    # ensure scheduler internal structures cleared
    async def _clear_scheduler():
        async with sched._lock:
            sched._jobs.clear()
            sched._heap.clear()
            sched._heap_map.clear()
            sched._wakeup.clear()
    # run the clear in loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_clear_scheduler())
    yield
    # teardown: stop scheduler if running
    loop.run_until_complete(sched.stop())
    # clear again
    loop.run_until_complete(_clear_scheduler())

@pytest.fixture
def monkeypatch_cron_doc(monkeypatch):
    # replace CronJobDoc in scheduler module with FakeCronJobDoc
    monkeypatch.setattr(scheduler_mod, "CronJobDoc", FakeCronJobDoc)
    # make find_one accept a lambda predicate for simplicity
    async def find_one_pred(predicate):
        for d in FakeCronJobDoc._store.values():
            try:
                if predicate(d):
                    return d
            except Exception:
                continue
        return None
    monkeypatch.setattr(FakeCronJobDoc, "find_one", classmethod(lambda cls, cond: find_one_pred(cond)))
    return monkeypatch

# ----------------------------
# Helper: ensure scheduler stopped and fresh
# ----------------------------
async def ensure_scheduler_stopped_and_clean():
    await sched.stop()
    async with sched._lock:
        sched._jobs.clear()
        sched._heap.clear()
        sched._heap_map.clear()
        sched._wakeup.clear()

# ----------------------------
# Tests
# ----------------------------
@pytest.mark.asyncio
async def test_no_duplicate_dispatch_on_update(monkeypatch_cron_doc):
    """
    场景：
    1. create job -> heap push entry A (next = now + 0.15s)
    2. update job immediately -> push entry B (next = same now + 0.15s)
    期望：到点时只触发一次 dispatch（task_manager.create_task 被调用一次）。
    """

    # control next-run times: both add and update return the same next datetime
    base_next = datetime.now(timezone.utc) + timedelta(seconds=0.15)

    async def fake_compute_next(cron_expr, tz_name=None, base=None):
        # always return same datetime (simulate duplicate entries)
        return base_next

    monkeypatch_cron_doc.setattr(scheduler_mod, "_compute_next", fake_compute_next, raising=False)
    # Also patch via sched instance method (some calls call self._compute_next)
    monkeypatch_cron_doc.setattr(sched, "_compute_next", fake_compute_next, raising=False)

    # Replace task_manager.create_task to just count calls
    call_counter = {"count": 0}

    async def fake_create_task(name, params, coro_fn):
        # simulate minimal create_task: just increment and return immediately
        call_counter["count"] += 1
        # do not actually run coro_fn; we only assert create_task called once
        await asyncio.sleep(0)  # keep it async
        return {"name": name}

    monkeypatch_cron_doc.setattr(scheduler_mod, "task_manager", type("TM", (), {"create_task": staticmethod(fake_create_task)}))

    # Start scheduler
    await ensure_scheduler_stopped_and_clean()
    await sched.start()

    # Add a job
    job_id = await sched.add_job(task_name="mytask", cron="* * * * *", params={})
    # Update the same job quickly, causing a second heap entry with same next timestamp
    success = await sched.update_job(job_id, params={"x": 1})
    assert success is True

    # wait enough time for the scheduler to trigger (0.15 + margin)
    await asyncio.sleep(0.5)

    # assert only one dispatch (create_task) happened
    assert call_counter["count"] == 1, f"expected 1 dispatch but got {call_counter['count']}"

    # cleanup
    await sched.stop()

@pytest.mark.asyncio
async def test_no_duplicate_dispatch_on_concurrent_enable(monkeypatch_cron_doc):
    """
    场景：
    - job exists but disabled.
    - two concurrent enable_job calls may push two entries with nearly same timestamp.
    期望：最终到点仍只 dispatch 一次。
    """
    # Prepare a disabled job in DB (FakeCronJobDoc)
    job_id = "job-enable-test"
    disabled_doc = FakeCronJobDoc(job_id=job_id, task_name="t", cron="* * * * *", params={}, tz="Asia/Shanghai", enabled=False)
    # Manually set store
    FakeCronJobDoc._store[job_id] = disabled_doc

    # compute_next will return a near-future time
    next_dt = datetime.now(timezone.utc) + timedelta(seconds=0.12)
    async def fake_compute_next(cron_expr, tz_name=None, base=None):
        return next_dt

    monkeypatch_cron_doc.setattr(scheduler_mod, "_compute_next", fake_compute_next, raising=False)
    monkeypatch_cron_doc.setattr(sched, "_compute_next", fake_compute_next, raising=False)

    # mock create_task
    call_counter = {"count": 0}
    async def fake_create_task(name, params, coro_fn):
        call_counter["count"] += 1
        await asyncio.sleep(0)
        return {"name": name}
    monkeypatch_cron_doc.setattr(scheduler_mod, "task_manager", type("TM", (), {"create_task": staticmethod(fake_create_task)}))

    # Start scheduler
    await ensure_scheduler_stopped_and_clean()
    await sched.start()

    # Call enable_job concurrently twice
    await asyncio.gather(
        sched.enable_job(job_id),
        sched.enable_job(job_id),
    )

    # wait to allow dispatch
    await asyncio.sleep(0.5)

    assert call_counter["count"] == 1, f"expected single dispatch after concurrent enable, got {call_counter['count']}"

    await sched.stop()

@pytest.mark.asyncio
async def test_run_once_triggers_dispatch_without_double(monkeypatch_cron_doc):
    """
    run_once 应立即触发一次调度（即使 heap 中也存在即将到点的 entry），并且不会与正常到点的 dispatch 导致双重 dispatch。
    我们模拟：先 add_job（next in ~0.2s），然后立即 run_once -> 应至少触发一次（run_once），而到点时不应再触发第二次。
    """
    # compute_next for add_job and reschedule will give future times
    next_dt = datetime.now(timezone.utc) + timedelta(seconds=0.2)
    async def fake_compute_next(cron_expr, tz_name=None, base=None):
        return next_dt
    monkeypatch_cron_doc.setattr(scheduler_mod, "_compute_next", fake_compute_next, raising=False)
    monkeypatch_cron_doc.setattr(sched, "_compute_next", fake_compute_next, raising=False)

    # patch task_manager.create_task to increment and simulate actual work
    call_counter = {"count": 0}
    async def fake_create_task(name, params, coro_fn):
        # When run_once triggers _safe_dispatch_and_reschedule -> _dispatch_job -> task_manager.create_task
        call_counter["count"] += 1
        # simulate created task running the coro_fn quickly so that rescheduling also happens
        await asyncio.sleep(0)
        return {"name": name}
    monkeypatch_cron_doc.setattr(scheduler_mod, "task_manager", type("TM", (), {"create_task": staticmethod(fake_create_task)}))

    # Start scheduler
    await ensure_scheduler_stopped_and_clean()
    await sched.start()

    # Add job then run_once immediately
    job_id = await sched.add_job(task_name="runonce-task", cron="* * * * *", params={})
    fired = await sched.run_once(job_id)
    assert fired is True

    # Wait longer than the scheduled time to ensure main loop does not dispatch again
    await asyncio.sleep(0.6)

    assert call_counter["count"] == 1, f"expected exactly 1 dispatch (run_once), got {call_counter['count']}"

    await sched.stop()
