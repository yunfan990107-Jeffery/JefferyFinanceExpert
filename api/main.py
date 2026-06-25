"""FastAPI 薄 API 层 —— 给 Web 前端提供数据接口。

启动：uvicorn api.main:app --reload --port 8000
所有业务逻辑复用 core/ 层，这里只做 HTTP 转接 + CORS。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from core import data_fetcher, intel, calibration, portfolio
from core.feishu_client import FeishuClient
from core.config import config
from core.stock_research import research_stock

app = FastAPI(title="PrivateFinanceExpert API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

fc = FeishuClient()


@app.on_event("startup")
def warmup_cache():
    """启动时预拉持仓股 K 线，预热 SQLite 缓存。后续请求毫秒级返回。"""
    import logging
    log = logging.getLogger("uvicorn")
    try:
        positions = fc.list_records(config.table_portfolio)
        codes = {p.get("code") for p in positions if p.get("code")}
        log.info(f"预热 K 线缓存：{len(codes)} 只持仓股...")
        for code in codes:
            data_fetcher.get_kline(code, days=60)
        log.info("K 线缓存预热完成")
    except Exception as e:
        log.warning(f"缓存预热跳过: {e}")


# ═══════════════════════════════════════════════════════════════════
# 市场概览
# ═══════════════════════════════════════════════════════════════════


@app.get("/api/market/overview")
def market_overview():
    """市场全局统计（涨跌家数等）。"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        up_count = int((df["涨跌幅"] > 0).sum())
        down_count = int((df["涨跌幅"] < 0).sum())
        flat_count = int((df["涨跌幅"] == 0).sum())
        return {
            "data": {
                "up_count": up_count,
                "down_count": down_count,
                "flat_count": flat_count,
                "total": len(df),
            }
        }
    except Exception as e:
        return {"data": None, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# 新闻/信息
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/news")
def get_news(keyword: str = "A股", limit: int = 10):
    """获取并处理新闻（含 AI 分级）。"""
    results = intel.fetch_and_process(keyword, limit=limit)
    return {"data": results}


@app.get("/api/news/raw")
def get_news_raw(keyword: str = "A股", limit: int = 20):
    """获取原始新闻（不经过 AI 分级，节省 token）。"""
    news = data_fetcher.get_news(keyword, limit=limit)
    return {"data": news}


# ═══════════════════════════════════════════════════════════════════
# 持仓
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/portfolio")
def get_portfolio():
    """获取当前持仓 + 实时市值计算。"""
    try:
        records = fc.list_records(config.table_portfolio)
    except Exception as e:
        return {"data": [], "error": str(e)}

    positions = []
    for r in records:
        f = r.get("fields", {})
        code = f.get("code", "")
        if not code:
            continue
        positions.append({
            "code": code,
            "name": f.get("name", ""),
            "qty": float(f.get("qty", 0)),
            "cost": float(f.get("cost", 0)),
            "industry": f.get("industry", "未分类"),
        })

    prices = {}
    for p in positions:
        price_data = data_fetcher.get_price(p["code"])
        if price_data.get("price"):
            prices[p["code"]] = price_data["price"]

    enriched = portfolio.compute_position_metrics(positions, prices)
    conc = portfolio.concentration(enriched)

    total_value = sum(e["market_value"] for e in enriched)
    total_cost = sum(e["cost"] * e["qty"] for e in enriched)
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0

    return {
        "data": {
            "positions": enriched,
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "concentration": conc,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 判断 & 复盘
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/judgments")
def get_judgments(status: str = None):
    """获取判断列表（可选按状态筛选）。"""
    try:
        records = fc.list_records(config.table_judgments)
    except Exception as e:
        return {"data": [], "error": str(e)}

    results = []
    for r in records:
        f = r.get("fields", {})
        item = {
            "record_id": r.get("record_id", ""),
            "target": f.get("target", ""),
            "direction": f.get("direction", ""),
            "confidence": f.get("confidence", 0),
            "horizon": f.get("horizon", ""),
            "basis": f.get("basis", ""),
            "falsify": f.get("falsify", ""),
            "verify_date": f.get("verify_date", ""),
            "actual_result": f.get("actual_result", ""),
            "brier_score": f.get("brier_score", None),
            "status": f.get("status", "待验证"),
            "created": f.get("created", ""),
        }
        if status and item["status"] != status:
            continue
        results.append(item)

    return {"data": results}


@app.get("/api/judgments/due")
def get_due_judgments():
    """获取到期待复盘的判断。"""
    try:
        records = fc.get_due_judgments(config.table_judgments)
        return {"data": records}
    except Exception as e:
        return {"data": [], "error": str(e)}


@app.post("/api/judgments")
def create_judgment(body: dict):
    """创建新判断。"""
    from core.calibration import make_verify_date
    from datetime import date as dt_date

    fields = {
        "target": body.get("target", ""),
        "direction": body.get("direction", ""),
        "confidence": int(body.get("confidence", 50)),
        "horizon": body.get("horizon", "1周"),
        "basis": body.get("basis", ""),
        "falsify": body.get("falsify", ""),
        "status": "待验证",
        "created": dt_date.today().isoformat(),
        "verify_date": make_verify_date(body.get("horizon", "1周")),
    }
    try:
        record_id = fc.add_record(config.table_judgments, fields)
        return {"record_id": record_id}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# 校准
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/calibration/summary")
def calibration_summary():
    """获取校准统计。"""
    try:
        records = fc.list_records(config.table_judgments)
    except Exception as e:
        return {"data": None, "error": str(e)}

    judgments = []
    for r in records:
        f = r.get("fields", {})
        if f.get("brier_score") is not None:
            judgments.append({
                "confidence": f.get("confidence", 50),
                "actual_result": f.get("actual_result", ""),
                "brier_score": f.get("brier_score"),
                "target": f.get("target", ""),
            })

    if not judgments:
        return {"data": {"avg_brier": None, "count": 0, "buckets": []}}

    summary = calibration.calibration_summary(judgments)
    bias = calibration.detect_bias_by_target(judgments)

    return {
        "data": {
            **summary,
            "bias_by_target": bias,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 个股研究
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/research/{code}")
def stock_research(code: str):
    """触发个股深度研究。"""
    try:
        report = research_stock(code)
        return {"data": report}
    except Exception as e:
        return {"data": None, "error": str(e)}


@app.get("/api/stock/price/{code}")
def stock_price(code: str):
    """获取个股最新价格。"""
    result = data_fetcher.get_price(code)
    return {"data": result}


@app.get("/api/stock/kline/{code}")
def stock_kline(code: str, days: int = 60):
    """获取个股K线。"""
    result = data_fetcher.get_kline(code, days=days)
    return {"data": result}


@app.get("/api/market/indices")
def market_indices():
    """获取主要指数行情。"""
    import sqlite3
    from pathlib import Path
    db = Path(__file__).resolve().parent.parent / "data" / "market_data.sqlite"
    conn = sqlite3.connect(str(db))
    codes = ["000001","399001","399006","000688","000300","000016"]
    names = {"000001":"上证指数","399001":"深证成指","399006":"创业板指","000688":"科创50","000300":"沪深300","000016":"上证50"}
    market_map = {"000001":"A股","399001":"A股","399006":"A股","000688":"A股","000300":"A股","000016":"A股"}
    result = []
    for code in codes:
        row = conn.execute(
            "SELECT close, date FROM daily_k WHERE code=? ORDER BY date DESC LIMIT 2",
            (code,),
        ).fetchall()
        if row and len(row) >= 1:
            latest = row[0]
            prev = row[1] if len(row) > 1 else latest
            change_pct = round((latest[0] - prev[0]) / prev[0] * 100, 2) if prev[0] else 0
            result.append({
                "name": names.get(code, code), "code": code,
                "price": round(latest[0], 2), "change_pct": change_pct,
                "market": market_map.get(code, ""),
            })
    conn.close()
    return {"data": result}


@app.get("/api/stock/fundamentals/{code}")
def stock_fundamentals(code: str):
    """获取个股基本面。"""
    result = data_fetcher.get_fundamentals(code)
    return {"data": result}


@app.get("/api/stock/search")
def stock_search(q: str = ""):
    """按名称或代码搜索股票，返回 [{code, name}, ...]"""
    if len(q) < 1:
        return {"data": []}
    result = data_fetcher.search_stock(q)
    return {"data": result}


# ═══════════════════════════════════════════════════════════════════
# 概念板块
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/concept/stock/{code}")
def stock_concepts(code: str):
    """查询股票所属概念板块。"""
    result = data_fetcher.get_stock_concepts(code)
    return {"data": result}


@app.get("/api/concept/{code}/stocks")
def concept_stocks(code: str):
    """查询概念板块成分股。"""
    result = data_fetcher.get_concept_stocks(code)
    return {"data": result}


@app.get("/api/concept/{code}/kline")
def concept_kline(code: str, days: int = 60):
    """查询概念板块日K线。"""
    result = data_fetcher.get_concept_kline(code, days=days)
    return {"data": result}


@app.get("/api/concept/fund_flow")
def concept_fund_flow(concept_code: str = "", limit: int = 30):
    """查询概念板块资金流向。"""
    result = data_fetcher.get_concept_fund_flow(concept_code, limit=limit)
    return {"data": result}


# ═══════════════════════════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm_ready": config.llm_ready(),
        "feishu_ready": True,
    }
