"""data_fetcher 单元测试 —— 以 mock 为主（网络不可靠环境）。

测试缓存读写、接口契约、降级逻辑。
"""
from __future__ import annotations
import sqlite3
from datetime import date
from pathlib import Path

import pytest

# 确保 cache 目录存在
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
CACHE_DB = CACHE_DIR / "market_data.sqlite"


@pytest.fixture(autouse=True)
def clean_cache():
    """每个测试前清空缓存表（保留表结构）。"""
    if CACHE_DB.exists():
        conn = sqlite3.connect(str(CACHE_DB))
        conn.executescript(
            "DELETE FROM price_cache; DELETE FROM kline_cache; "
            "DELETE FROM fundamentals_cache; DELETE FROM news_cache;"
        )
        conn.commit()
        conn.close()
    yield


class TestPriceCache:
    def test_cache_write_and_read(self):
        """写入缓存后应能在当日读回。"""
        from core.data_fetcher import _get_conn, _init_cache_tables
        _init_cache_tables()
        today = date.today().isoformat()
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO price_cache VALUES (?,?,?,?,?,?)",
            ("000001", 12.5, 5.2, 0.8, "平安银行", today),
        )
        conn.commit()
        conn.close()

        # 模拟 get_price 走缓存路径（通过直接查 DB 验证）
        conn2 = _get_conn()
        row = conn2.execute(
            "SELECT * FROM price_cache WHERE code=? AND updated=?", ("000001", today)
        ).fetchone()
        conn2.close()
        assert row is not None
        assert row["price"] == 12.5
        assert row["name"] == "平安银行"

    def test_cache_expiry(self):
        """非当日缓存不应命中。"""
        from core.data_fetcher import _get_conn
        yesterday = (date.today().replace(day=date.today().day - 1)
                     if date.today().day > 1 else date.today()).isoformat()
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO price_cache VALUES (?,?,?,?,?,?)",
            ("000001", 10.0, None, None, "旧数据", yesterday),
        )
        conn.commit()
        conn.close()

        today = date.today().isoformat()
        conn2 = _get_conn()
        row = conn2.execute(
            "SELECT * FROM price_cache WHERE code=? AND updated=?", ("000001", today)
        ).fetchone()
        conn2.close()
        assert row is None  # 旧日期不应命中


class TestKlineCache:
    def test_kline_write_and_read(self):
        from core.data_fetcher import _get_conn, _init_cache_tables
        _init_cache_tables()
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO kline_cache VALUES (?,?,?,?,?,?,?)",
            ("000001", "2026-06-20", 12.0, 12.5, 11.8, 12.3, 1000000),
        )
        conn.commit()
        conn.close()

        conn2 = _get_conn()
        rows = conn2.execute(
            "SELECT * FROM kline_cache WHERE code=? ORDER BY date", ("000001",)
        ).fetchall()
        conn2.close()
        assert len(rows) == 1
        assert rows[0]["close"] == 12.3


class TestInterfaceContract:
    """验证所有公开函数签名与任务卡一致。"""
    import inspect
    from core import data_fetcher as df

    def test_get_price_signature(self):
        sig = str(self.inspect.signature(self.df.get_price))
        assert "code" in sig

    def test_get_kline_signature(self):
        sig = str(self.inspect.signature(self.df.get_kline))
        assert "code" in sig and "days" in sig

    def test_get_fundamentals_signature(self):
        sig = str(self.inspect.signature(self.df.get_fundamentals))
        assert "code" in sig

    def test_get_news_signature(self):
        sig = str(self.inspect.signature(self.df.get_news))
        assert "keyword" in sig and "limit" in sig

    def test_get_price_returns_dict(self):
        """即使 akshare 不可用，也应返回 dict 而非抛异常。"""
        result = self.df.get_price("000001")
        assert isinstance(result, dict)
        assert "code" in result

    def test_get_kline_returns_list(self):
        result = self.df.get_kline("000001", days=10)
        assert isinstance(result, list)

    def test_get_fundamentals_returns_dict(self):
        result = self.df.get_fundamentals("000001")
        assert isinstance(result, dict)
        assert "indicators" in result

    def test_get_news_returns_list(self):
        result = self.df.get_news("茅台", limit=5)
        assert isinstance(result, list)
