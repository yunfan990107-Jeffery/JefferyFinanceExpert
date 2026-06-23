"""基础调用日志（observability）。

统一的轻量日志器：外部调用（LLM / 飞书 / 数据源）在关键点记一行，
失败时可见、token/耗时可追。日志同时输出到控制台和 logs/app.log（已 gitignore）。

用法：
    from .obs import log_event
    log_event("llm_call", model="deepseek-chat", ok=True)
    log_event("llm_error", error=str(e))
"""
from __future__ import annotations
import logging
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

_logger = logging.getLogger("pfe")
if not _logger.handlers:
    _logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(_LOG_DIR / "app.log", encoding="utf-8")
    fh.setFormatter(fmt)
    _logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    _logger.addHandler(sh)


def log_event(kind: str, level: str = "info", **fields) -> None:
    """记录一条结构化事件。kind=事件类型，fields=附加字段。"""
    parts = [kind] + [f"{k}={v}" for k, v in fields.items()]
    msg = " ".join(parts)
    getattr(_logger, level if level in ("info", "warning", "error") else "info")(msg)
