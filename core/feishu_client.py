"""飞书多维表格（Bitable）读写封装 —— 通过 subprocess 调用本机 lark-cli 实现。

所有方法操作的是 config 中的 bitable_app_token 下的各 table。
保持本类的方法签名稳定——上层 app/ 与 core/ 依赖它。
"""
from __future__ import annotations
import json
import subprocess
from datetime import date
from .config import config


class FeishuClient:
    def __init__(self, app_id: str = "", app_secret: str = "", app_token: str = ""):
        self.app_id = app_id or config.app_id
        self.app_secret = app_secret or config.app_secret
        self.app_token = app_token or config.bitable_app_token

    # ── 内部工具 ──────────────────────────────────────────────

    def _cli(self, *args: str) -> dict:
        """执行 lark-cli 命令，返回 response['data'] 或 response 自身。

        Windows 下 lark-cli 是 .CMD 脚本，需通过 cmd /c 启动。
        """
        cli_args = ["lark-cli"] + list(args)
        try:
            result = subprocess.run(
                cli_args, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=30,
            )
        except FileNotFoundError:
            # Windows: .CMD 文件不能直接被 CreateProcess 执行，用 cmd /c 重试
            try:
                result = subprocess.run(
                    ["cmd", "/c"] + cli_args,
                    capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=30,
                )
            except FileNotFoundError:
                raise RuntimeError("lark-cli 未安装或不在 PATH 中，请先配置 lark-cli")
        except subprocess.TimeoutExpired:
            raise RuntimeError("lark-cli 命令超时 (30s)")

        if result.returncode != 0:
            raise RuntimeError(
                f"lark-cli 返回非 0 (rc={result.returncode}): {result.stderr.strip()}"
            )
        try:
            resp = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(
                f"lark-cli 返回非 JSON 输出: {result.stdout[:300]}"
            )
        if not resp.get("ok"):
            err = resp.get("error", {})
            raise RuntimeError(
                f"lark-cli API 错误: {err.get('message', 'unknown')}"
            )
        return resp.get("data", resp)

    @staticmethod
    def _unwrap_cell(cell):
        """将单选项数组解包为纯文本；多元素数组/None/其他原样返回。"""
        if isinstance(cell, list) and len(cell) == 1 and isinstance(cell[0], str):
            return cell[0]
        return cell

    def _parse_records(self, data: dict) -> list[dict]:
        """把 record-list JSON 返回体转为 [{record_id, field...}, ...] 列表。"""
        fields = data.get("fields", [])
        rows = data.get("data", [])
        record_ids = data.get("record_id_list", [])
        result = []
        for i, row in enumerate(rows):
            rec = {"record_id": record_ids[i] if i < len(record_ids) else ""}
            for j, field_name in enumerate(fields):
                if j < len(row):
                    rec[field_name] = self._unwrap_cell(row[j])
            result.append(rec)
        return result

    # ── 公开接口 ──────────────────────────────────────────────

    def add_record(self, table_id: str, fields: dict) -> str:
        """新增一条记录，返回 record_id。"""
        payload = json.dumps(fields, ensure_ascii=False)
        resp = self._cli(
            "base", "+record-upsert",
            "--base-token", self.app_token,
            "--table-id", table_id,
            "--json", payload,
        )
        record_ids = resp.get("record", {}).get("record_id_list", [])
        if not record_ids:
            raise RuntimeError("add_record 未返回 record_id")
        return record_ids[0]

    def update_record(self, table_id: str, record_id: str, fields: dict) -> None:
        """更新指定记录的字段。"""
        payload = json.dumps(fields, ensure_ascii=False)
        self._cli(
            "base", "+record-upsert",
            "--base-token", self.app_token,
            "--table-id", table_id,
            "--record-id", record_id,
            "--json", payload,
        )

    def list_records(self, table_id: str, filter_: dict | None = None) -> list[dict]:
        """列出记录；可选 Python 侧过滤。

        返回 [{record_id, field_name: value, ...}, ...]。
        单选项字段自动解包为字符串。
        """
        resp = self._cli(
            "base", "+record-list",
            "--base-token", self.app_token,
            "--table-id", table_id,
            "--format", "json",
            "--limit", "200",
        )
        records = self._parse_records(resp)
        # 简单分页兜底（通常 P0 数据量不会超过 200）
        if resp.get("has_more"):
            # TODO(P1): 实现完整分页
            pass
        if filter_:
            records = [
                r for r in records
                if all(r.get(k) == v for k, v in filter_.items())
            ]
        return records

    def get_due_judgments(self, today: date) -> list[dict]:
        """便捷方法：返回验证日期<=today 且 actual_result 为'待验证'的判断。"""
        all_judgments = self.list_records(config.table_judgments)
        today_str = today.isoformat()
        due = []
        for j in all_judgments:
            vd = j.get("verify_date", "")
            ar = j.get("actual_result", "")
            if vd and vd <= today_str and ar == "待验证":
                due.append(j)
        return due
