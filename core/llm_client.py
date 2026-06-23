"""LLM 调用封装 —— OpenAI 兼容 API（当前用 DeepSeek）。

统一入口（需要调 AI 的新功能都走这里，不要自行写 requests 调用）：
- chat(system_prompt, user_prompt)        通用调用，返回文本
- load_role(filename)                     读取 agents/<filename> 作 system prompt
- generate_review(judgment, actual_note)  复盘专用（复盘页用）

配置见 .env：LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
（DeepSeek：base=https://api.deepseek.com，model=deepseek-chat；OpenAI 兼容，无需改代码即可切换其它供应商）。
未配置 LLM 时自动降级为「返回提示词」，不报错。
"""
from __future__ import annotations
import json
from pathlib import Path
import requests
from .config import config
from .calibration import build_review_prompt

_AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"


def load_role(filename: str) -> str:
    """读取 agents/<filename> 作为 system prompt；不存在时返回兜底。

    供各功能加载角色，如 load_role("devil_advocate.md")、load_role("risk_control.md")。
    """
    path = _AGENTS_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "你是投资分析系统的 AI 角色，请按要求输出，不给买卖建议。"


def chat(system_prompt: str, user_prompt: str, max_tokens: int = 800) -> str:
    """通用 LLM 调用（OpenAI 兼容）。所有需要 AI 的功能都应走这里。

    未配置 LLM（config.llm_ready() 为 False）时降级：返回带提示词的占位文本，
    便于用户手动喂给 AI，而不是报错中断。
    """
    if not config.llm_ready():
        return (
            "（LLM 未配置：请在 .env 设置 LLM_API_KEY。以下为可手动喂给 AI 的提示词。）\n\n"
            f"--- system ---\n{system_prompt}\n\n--- user ---\n{user_prompt}"
        )
    try:
        resp = requests.post(
            f"{config.llm_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.llm_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": max_tokens,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except requests.RequestException as e:
        return f"（LLM 调用失败：{e}）"
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return f"（LLM 返回格式异常：{e}）"


def generate_review(judgment: dict, actual_note: str) -> str:
    """复盘专用：用 quality_review 角色对到期判断生成复盘文本。"""
    return chat(
        load_role("quality_review.md"),
        build_review_prompt(judgment, actual_note),
    )
