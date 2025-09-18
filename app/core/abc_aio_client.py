# file: app/clients/abstract_aio_client.py
import atexit
import asyncio
import logging
from typing import Optional, Dict, Any
from urllib.parse import urljoin

import aiohttp

logger = logging.getLogger(__name__)


class AioClientManager:
    """
    全局单例的会话管理器（按 context 隔离 cookies/headers/connector 等）。
    负责真实创建/维护 aiohttp.ClientSession。
    """
    _instance: Optional["AioClientManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, *,
                 default_timeout: int = 30,
                 default_connector_opts: Optional[Dict[str, Any]] = None):
        if getattr(self, "_inited", False):
            return
        self._inited = True

        self.default_timeout = aiohttp.ClientTimeout(total=default_timeout)
        self.default_connector_opts = default_connector_opts or {
            "limit": 200,
            "limit_per_host": 20,
            "keepalive_timeout": 75,
        }

        # context -> config dict
        self._configs: Dict[str, Dict[str, Any]] = {}
        # context -> session
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
        # context -> asyncio.Lock for creation
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    # 注册 context（同步方法，方便在子类 __init__ 中调用）
    def register_context(
        self,
        name: str,
        *,
        base_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        cookie_jar: Optional[aiohttp.CookieJar] = None,
        connector: Optional[aiohttp.TCPConnector] = None,
        timeout: Optional[aiohttp.ClientTimeout] = None,
        trust_env: bool = False,
    ):
        cfg = {
            "base_url": (base_url.rstrip("/") if base_url else "") if base_url is not None else "",
            "headers": dict(headers) if headers else {},
            "cookie_jar": cookie_jar,
            "connector": connector,
            "timeout": timeout,
            "trust_env": trust_env,
        }
        self._configs[name] = cfg
        logger.debug("Registered context %s -> %s", name, cfg)

    # 可选：在运行时更新 headers（异步安全）
    async def update_context_headers(self, name: str, headers: Dict[str, str], recreate: bool = True):
        async with self._global_lock:
            cfg = self._configs.get(name, {})
            cfg["headers"] = dict(headers)
            self._configs[name] = cfg
        if recreate:
            await self.close_context(name)

    async def _ensure_lock(self, name: str) -> asyncio.Lock:
        if name not in self._locks:
            self._locks[name] = asyncio.Lock()
        return self._locks[name]

    async def get_session(self, name: str = "default") -> aiohttp.ClientSession:
        # 先快速路径
        if name in self._sessions:
            return self._sessions[name]

        lock = await self._ensure_lock(name)
        async with lock:
            if name in self._sessions:
                return self._sessions[name]

            cfg = self._configs.get(name, {})
            timeout = cfg.get("timeout") or self.default_timeout
            connector = cfg.get("connector") or aiohttp.TCPConnector(**self.default_connector_opts)
            headers = cfg.get("headers") or {}
            cookie_jar = cfg.get("cookie_jar") or aiohttp.CookieJar()
            trust_env = cfg.get("trust_env", False)

            session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=headers,
                cookie_jar=cookie_jar,
                trust_env=trust_env,
            )
            self._sessions[name] = session
            logger.debug("Created session for context %s (headers=%s, connector=%s)", name, headers, connector)
            return session

    async def fetch_json(self, name: str, method: str, path: str, **kwargs) -> Any:
        session = await self.get_session(name)
        cfg = self._configs.get(name, {})
        base = cfg.get("base_url", "") or ""
        url = path if path.startswith("http") else urljoin(base + "/", path.lstrip("/"))
        request_headers = kwargs.pop("headers", None)
        async with session.request(method, url, headers=request_headers, **kwargs) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def fetch_text(self, name: str, method: str, path: str, **kwargs) -> str:
        session = await self.get_session(name)
        cfg = self._configs.get(name, {})
        base = cfg.get("base_url", "") or ""
        url = path if path.startswith("http") else urljoin(base + "/", path.lstrip("/"))
        request_headers = kwargs.pop("headers", None)
        async with session.request(method, url, headers=request_headers, **kwargs) as resp:
            resp.raise_for_status()
            return await resp.text()

    async def close_context(self, name: str):
        sess = self._sessions.pop(name, None)
        if sess and not sess.closed:
            await sess.close()
            logger.debug("Closed session for context %s", name)

    async def shutdown(self):
        for name, sess in list(self._sessions.items()):
            try:
                if sess and not sess.closed:
                    await sess.close()
                    logger.debug("Closed session %s", name)
            except Exception:
                logger.exception("Error closing session %s", name)
        self._sessions.clear()
        self._configs.clear()
        self._locks.clear()
        logger.info("AioClientManager shutdown complete.")


# module-level singleton (导入即可使用)
aio_client_manager = AioClientManager()


@atexit.register
def _cleanup_on_exit():
    try:
        asyncio.run(aio_client_manager.shutdown())
    except RuntimeError:
        # 如果已有事件循环在运行，则无法再 run，忽略（建议在应用 shutdown hook 显式调用 shutdown）
        pass


# ----------------- BaseAioClient: 供业务客户端继承 -----------------
class BaseAioClient:
    """
    业务客户端父类。子类可以在 __init__ 中调用 super().init(...)
    来注册到全局 aio_client_manager（同步操作）。
    """
    def __init__(self):
        self._context: Optional[str] = None

    def init(self,
             name: str,
             *,
             base_url: Optional[str] = None,
             headers: Optional[Dict[str, str]] = None,
             cookie_jar: Optional[aiohttp.CookieJar] = None,
             connector: Optional[aiohttp.TCPConnector] = None,
             timeout: Optional[aiohttp.ClientTimeout] = None,
             trust_env: bool = False):
        """
        在子类的 __init__ 里调用（同步）：
            super().init("pansou", base_url=..., headers=..., ...)
        该方法只做注册（不会立即创建 session）。
        """
        aio_client_manager.register_context(
            name,
            base_url=base_url,
            headers=headers,
            cookie_jar=cookie_jar,
            connector=connector,
            timeout=timeout,
            trust_env=trust_env,
        )
        self._context = name

    # 便捷代理方法（异步）
    async def fetch_json(self, method: str, path: str, **kwargs):
        if not self._context:
            raise RuntimeError("Client context not initialized; call super().init(...) in __init__")
        return await aio_client_manager.fetch_json(self._context, method, path, **kwargs)

    async def fetch_text(self, method: str, path: str, **kwargs):
        if not self._context:
            raise RuntimeError("Client context not initialized; call super().init(...) in __init__")
        return await aio_client_manager.fetch_text(self._context, method, path, **kwargs)

    async def close(self):
        if self._context:
            await aio_client_manager.close_context(self._context)
