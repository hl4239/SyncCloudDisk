# app/logging_config.py
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# try colorama for Windows compatibility
try:
    from colorama import init as _colorama_init, Fore, Style
    _colorama_init(autoreset=True)
    _HAS_COLORAMA = True
except Exception:
    _HAS_COLORAMA = False
    # minimal fallbacks (ANSI codes) — still works on most Unix terminals
    class _FakeStyle:
        RESET_ALL = "\033[0m"
    Style = _FakeStyle()
    Fore = type("F", (), {
        "CYAN": "\033[36m",
        "GREEN": "\033[32m",
        "YELLOW": "\033[33m",
        "RED": "\033[31m",
        "MAGENTA": "\033[35m",
        "BLUE": "\033[34m",
        "RESET": "\033[0m"
    })

class WholeLineColoredFormatter(logging.Formatter):
    """
    将整条格式化后的日志消息包上颜色（控制台使用）。
    不改变 record 本身，直接对最终字符串着色。
    """
    LEVEL_COLOR = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA,
    }

    def __init__(self, fmt=None, datefmt=None, style='%', use_color=True):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        # 先用父类生成完整未着色字符串（含时间、模块、行号等）
        formatted = super().format(record)
        if not self.use_color:
            return formatted
        color = self.LEVEL_COLOR.get(record.levelno, "")
        reset = Style.RESET_ALL if _HAS_COLORAMA else "\033[0m"
        return f"{color}{formatted}{reset}"

def find_project_root(start: Optional[Path] = None) -> Path:
    """
    向上查找最近包含 .git / pyproject.toml / setup.py / requirements.txt 的目录，
    找不到时返回当前工作目录。
    """
    if start is None:
        start = Path.cwd()
    current = start.resolve()
    markers = {".git", "pyproject.toml", "setup.py", "requirements.txt"}
    for parent in [current] + list(current.parents):
        if any((parent / m).exists() for m in markers):
            return parent
    return current  # fallback

def setup_logging(
    *,
    log_file: Optional[str] = None,
    console_level: int = logging.DEBUG,
    file_level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    fmt_console: str = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
    fmt_file: str = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
    datefmt: str = "%Y-%m-%d %H:%M:%S",
    root_level: int = logging.DEBUG,
    use_color: bool = True,
    project_root: Optional[Path] = None,
):
    """
    初始化日志，控制台整行上色，文件日志无色并写入项目根目录（默认）。
    - log_file: 若为 None，则自动使用项目根目录下 logs/app.log
    - project_root: 可传入显式 Path，否则自动查找
    """
    # determine project root
    pr = Path(project_root) if project_root else find_project_root()
    if log_file is None:
        log_dir = pr / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = str(log_dir / "app.log")
    else:
        # 如果传入相对路径，则确保相对于项目根
        lf = Path(log_file)
        if not lf.is_absolute():
            log_file = str((pr / lf).resolve())
        else:
            log_file = str(lf)

    # reset root handlers (防止重复注册)
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(root_level)

    # console handler with whole-line color
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(WholeLineColoredFormatter(fmt=fmt_console, datefmt=datefmt, use_color=use_color))
    root.addHandler(ch)

    # file handler (no color)
    try:
        file_parent = Path(log_file).parent
        file_parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(filename=log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        fh.setLevel(file_level)
        fh.setFormatter(logging.Formatter(fmt=fmt_file, datefmt=datefmt))
        root.addHandler(fh)
    except Exception:
        # 如果文件 handler 创建失败，也不要阻塞主程序
        logging.getLogger(__name__).exception("无法创建日志文件 handler，继续仅使用控制台日志")

    # 降低一些第三方模块噪音
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("prefect").setLevel(logging.WARNING)
    logging.getLogger('pymongo').setLevel(logging.WARNING)
    logging.getLogger('graphviz').setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)         # 只保留请求摘要，不要 DEBUG
    logging.getLogger("httpcore").setLevel(logging.WARNING)   # 屏蔽 httpcore 的细节
    logging.getLogger("websockets").setLevel(logging.WARNING) # 屏蔽 websockets 连接过程
    logging.getLogger("prefect").setLevel(logging.INFO)       # Prefect 只保留正常输出
    logging.getLogger('tensorflow').setLevel(logging.WARNING)
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

# quick test if run as script
if __name__ == "__main__":
    setup_logging()
    log = get_logger("demo")
    log.debug("调试消息")
    log.info("普通消息")
    log.warning("警告消息")
    log.error("错误消息，带异常示例", exc_info=True)
    log.critical("致命错误")
