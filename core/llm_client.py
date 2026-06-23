"""LLM 调用封装 —— OpenAI 兼容 API。

用于复盘中心：读取 agents/quality_review.md 作为 system prompt，
将 build_review_prompt 的输出作为 user prompt，调用 LLM 生成复盘文本。
"""
from __future__ import annotations
import json
from pathlib import Path
import requests
from .config import config
from .calibration import build_review_prompt

# agents/ 目录的相对路径
_AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"


def _load_quality_review_system_prompt() -> str:
    """读取质量审查角色的 system prompt。"""
    path = _AGENTS_DIR / "quality_review.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "你是投资分析系统的质量审查官。请对到期判断做复盘分析。"


def generate_review(judgment: dict, actual_note: str) -> str:
    """调用 LLM 生成复盘文本。

    Args:
        judgment: 判断记录 dict（含 content/direction/confidence/basis/falsify_cond）
        actual_note: 实际发生情况（用户填写）

    Returns:
        LLM 生成的复盘分析文本。
    """
    if not config.llm_ready():
        return (
            "（LLM 未配置：请在 .env 中设置 LLM_API_KEY。"
            "以下为可手动喂给 AI 的提示词。）\n\n"
            "--- 提示词 ---\n"
            + build_review_prompt(judgment, actual_note)
        )

    system_prompt = _load_quality_review_system_prompt()
    user_prompt = build_review_prompt(judgment, actual_note)

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
                "max_tokens": 800,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.RequestException as e:
        return f"（LLM 调用失败：{e}）"
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return f"（LLM 返回格式异常：{e}）"
