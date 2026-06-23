# T1-1 数据层（AkShare + SQLite 缓存）

**目标**：实现 `core/data_fetcher.py`，封装行情/财务取数，并用本地 SQLite 缓存可再生数据。
**要做什么**
- 取消 `requirements.txt` 中 `akshare` 注释并安装。
- 实现取数函数（见接口契约），数据缓存到 `cache/*.sqlite`（已 gitignore）。
- 缓存策略：当日已缓存则不重复请求；缓存表见开发文档 4.2（kline / fundamentals）。
**接口契约（新增，确定后勿改签名）**
- `get_price(code: str) -> float`　最新价
- `get_kline(code: str, days: int = 300) -> list[dict]`　每条含 date/open/high/low/close/vol
- `get_fundamentals(code: str) -> dict`　关键财务：营收/净利/ROE/负债率/PE/PB
- `get_news(keyword: str, limit: int = 20) -> list[dict]`（可选，供 T1-5 复用）
**工具**：akshare、sqlite3、pandas。
**交付/验收**：能取到某股现价/K线/财务；二次调用走缓存（可验证不重复请求）；新增 mock 单测；`pytest -q` 全绿；满足 Global DoD。
**依赖**：无（可并行）。**下游**：T1-2、T1-3、T1-5。
