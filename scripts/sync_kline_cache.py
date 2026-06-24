#!/usr/bin/env python
"""批量同步 K 线到本地 SQLite —— 一次跑完，以后只增量。

用法：
    python scripts/sync_kline_cache.py                    # 同步持仓股
    python scripts/sync_kline_cache.py --all              # 全市场（慎用，耗时很长）
    python scripts/sync_kline_cache.py --codes 600519,000001  # 指定代码

首次运行拉取历史数据写入 data/market_data.sqlite。
后续每天跑一次只需增量（缓存当日已有则跳过）。
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import data_fetcher
from core.feishu_client import FeishuClient
from core.config import config


def sync(codes: list[str], days: int = 365):
    """批量拉取 K 线，写入 SQLite 缓存。"""
    total = len(codes)
    for i, code in enumerate(codes):
        print(f"[{i+1}/{total}] {code} ... ", end="", flush=True)
        try:
            result = data_fetcher.get_kline(code.strip(), days=days)
            print(f"{len(result)} 条")
        except Exception as e:
            print(f"失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="批量同步 K 线到本地缓存")
    parser.add_argument("--all", action="store_true", help="全市场（非常慢）")
    parser.add_argument("--codes", type=str, help="逗号分隔的代码，如 600519,000001")
    parser.add_argument("--days", type=int, default=365, help="拉取天数（默认365）")
    args = parser.parse_args()

    codes: list[str] = []

    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    elif args.all:
        # 全市场：从 AkShare 取代码列表
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
            codes = df["代码"].tolist()
            print(f"全市场 {len(codes)} 只股票，预计耗时很长...")
        except Exception as e:
            print(f"获取全市场代码失败: {e}")
            sys.exit(1)
    else:
        # 默认：同步飞书持仓 + 常见指数
        try:
            fc = FeishuClient()
            positions = fc.list_records(config.table_portfolio)
            codes = [p["code"] for p in positions if p.get("code")]
        except Exception:
            pass
        # 加常见基准
        codes += ["000001", "399001", "399006", "000300", "000905"]
        codes = list(dict.fromkeys(codes))  # 去重

    if not codes:
        print("没有需要同步的代码。用 --codes 指定或 --all 全市场。")
        return

    print(f"同步 {len(codes)} 只标的，各拉 {args.days} 天 K 线...")
    sync(codes, args.days)
    print("完成。")


if __name__ == "__main__":
    main()
