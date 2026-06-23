"""Agent 注册表 —— 解析 agents/*.md 的 YAML frontmatter。

每个 agent 文件开头为 YAML frontmatter（--- 包裹），字段：
  name        agent 名称
  team        所属团队（review / support / research 等）
  inputs      输入数据依赖 [key1, key2, ...]
  tools       可调用工具名 [tool_name, ...]
  model_tier  模型等级（cheap / strong）
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path

_AGENTS_DIR = Path(__file__).resolve().parent

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class AgentSpec:
    name: str
    team: str = ""
    inputs: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    model_tier: str = "cheap"
    prompt: str = ""  # YAML 之后的所有内容（system prompt）


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """解析 YAML frontmatter，返回 (meta_dict, prompt_text)。"""
    m = FRONTMATTER_RE.match(text)
    if not m:
        # 无 frontmatter，取文件名作 name
        return {}, text
    # 简易 YAML 解析（不依赖 PyYAML）
    meta = {}
    for line in m.group(1).strip().split("\n"):
        line = line.strip()
        if ":" in line:
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if v.startswith("[") and v.endswith("]"):
                v = [x.strip() for x in v[1:-1].split(",") if x.strip()]
            meta[k] = v
    return meta, text[m.end():]


def get_agent(name: str) -> AgentSpec | None:
    """按名称获取 agent 配置。"""
    for f in _AGENTS_DIR.glob("*.md"):
        spec = _load_agent_file(f)
        if spec and spec.name == name:
            return spec
    return None


def list_agents(team: str | None = None) -> list[AgentSpec]:
    """列出所有 agent，可按 team 过滤。"""
    agents = []
    for f in _AGENTS_DIR.glob("*.md"):
        spec = _load_agent_file(f)
        if spec:
            if team is None or spec.team == team:
                agents.append(spec)
    return agents


def _load_agent_file(path: Path) -> AgentSpec | None:
    raw = path.read_text(encoding="utf-8")
    meta, prompt = _parse_frontmatter(raw)
    name = meta.get("name", path.stem)
    return AgentSpec(
        name=name,
        team=meta.get("team", ""),
        inputs=meta.get("inputs", []),
        tools=meta.get("tools", []),
        model_tier=meta.get("model_tier", "cheap"),
        prompt=prompt.strip(),
    )
