#!/usr/bin/env python
"""本地 Markdown → 飞书知识库 Wiki 文档（纯脚本，零 LLM 调用）。

用法：
    python scripts/push_report_to_feishu.py <local_md> [--title 标题] [--parent wiki_node_token]

示例：
    python scripts/push_report_to_feishu.py research/research_memo_600519.md --title "茅台研究-20260623"

规则：
    - 全程不经过任何 LLM/MCP-agent，纯 lark-cli subprocess。
    - 内容通过 @file 传参，不进命令行，不经过模型 token 化。
    - 文档必须挂在知识库（/wiki/），遵守 docs/README「飞书资源归属」。
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

# 知识库配置（来自 docs/README「飞书资源归属」）
SPACE_ID = "7652969095092014047"
DEFAULT_PARENT = "E7G9wNDvYiMCQLkHRGEcF0APnLf"


def _cli(*args: str) -> dict:
    """执行 lark-cli，返回 parsed JSON data。"""
    result = subprocess.run(
        ["cmd", "/c", "lark-cli"] + list(args),
        capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"lark-cli 失败: {result.stderr.strip()[:300]}")
    resp = json.loads(result.stdout)
    if not resp.get("ok"):
        raise RuntimeError(resp.get("error", {}).get("message", str(resp)))
    return resp.get("data", resp)


def push_markdown_to_wiki(
    md_path: str,
    title: str,
    parent: str = DEFAULT_PARENT,
) -> str:
    """将本地 .md 文件推送到飞书知识库，返回 /wiki/ 链接。

    Args:
        md_path: 本地 Markdown 文件路径。
        title: 文档标题。
        parent: 父 wiki 节点 token（默认知识库根节点）。

    Returns:
        Wiki URL（如 https://xxx.feishu.cn/wiki/xxx）。
    """
    md_file = Path(md_path).resolve()
    if not md_file.exists():
        raise FileNotFoundError(f"文件不存在: {md_path}")

    # lark-cli 要求 @file 为相对路径，故转为相对路径
    try:
        rel_path = md_file.relative_to(Path.cwd())
    except ValueError:
        # 不在当前目录下，复制到临时文件
        import tempfile, shutil
        tmp = tempfile.NamedTemporaryFile(
            suffix=".md", delete=False, encoding="utf-8", mode="w"
        )
        tmp.write(md_file.read_text(encoding="utf-8"))
        tmp.close()
        rel_path = Path(tmp.name)
    md_ref = str(rel_path).replace("\\", "/")

    # 1. 建 wiki 节点（docx 类型）
    node = _cli(
        "wiki", "+node-create",
        "--space-id", SPACE_ID,
        "--parent-node-token", parent,
        "--obj-type", "docx",
        "--title", title,
    )
    obj_token = node.get("obj_token", "")
    wiki_url = node.get("url", "")
    if not obj_token:
        raise RuntimeError("wiki +node-create 未返回 obj_token")

    # 2. 写入内容（@file 相对路径传参）
    _cli(
        "docs", "+update",
        "--doc", obj_token,
        "--command", "append",
        "--doc-format", "markdown",
        "--content", f"@{md_ref}",
    )

    return wiki_url


def main():
    parser = argparse.ArgumentParser(
        description="推送本地 Markdown 到飞书知识库 Wiki",
    )
    parser.add_argument("md_path", help="本地 .md 文件路径")
    parser.add_argument("--title", default=None, help="文档标题（默认取文件名）")
    parser.add_argument(
        "--parent", default=DEFAULT_PARENT,
        help=f"父 wiki 节点 token（默认: {DEFAULT_PARENT}）",
    )
    args = parser.parse_args()

    title = args.title or Path(args.md_path).stem
    try:
        url = push_markdown_to_wiki(args.md_path, title, args.parent)
        print(f"✅ 已推送: {url}")
    except Exception as e:
        print(f"❌ 失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
