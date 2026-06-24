# 变更日志（CHANGELOG）

> 面向 AI agent 的可读变更记录。每完成一项重要改动，在顶部新增一节。
> 人类可读的简要记录见 `docs/DEVLOG.md`。

---

## [2026-06-25] K 线数据源切换：Baostock → 通达信 pytdx

### 背景

项目原有 K 线建库脚本 `scripts/build_kline_db.py` 依赖 Baostock 批量下载全市场 A 股日 K 线，存在以下问题：

1. **Baostock 反爬严格**：短时间多次 login/logout 会触发 IP 黑名单（"黑名单用户，请与管理员联系"）
2. **AkShare 依赖东方财富域名**：`push2.eastmoney.com` 和 `push2his.eastmoney.com` 在部分网络环境被墙或限流
3. **速度慢**：Baostock 每只股票需分年请求，全量 1-3 小时
4. **腾讯源 `stock_zh_a_hist_tx`** 单线程可用但多线程全失败（`gu.qq.com` 对并发敏感）

### 改动

#### 1. `scripts/build_kline_db.py` — 完全重写

- **数据源**：改用 `pytdx` 直连通达信行情服务器（TCP socket，非 HTTP）
  - 通达信服务器 IP：`218.75.126.9:7709`（主）、另有 4 个备选
  - 新依赖：`pytdx>=1.72`
- **代码列表**：`get_security_count()` + `get_security_list()` 获取全市场代码
  - 沪市（market=1）从 offset 20000 开始扫描（前 20000 条为板块/指数/债券等非股票条目）
  - 深市（market=0）从 offset 0 开始
  - 通过 `A_SHARE_PREFIXES` 过滤：`600/601/603/605/688/000/001/002/003/300/301`
- **K 线下载**：`get_security_bars(9, market, code, 0, count)` 取日线
  - 每条 0.02 秒，4 线程 5200 只股票 3.9 分钟完成
- **线程安全**：`threading.local()` 为每个线程维护独立的 TDX 连接
- **新增参数**：`--years N`（拉最近 N 年）、`--server IP`（指定服务器）

#### 2. `requirements.txt` — 新增 pytdx

```diff
+ # 通达信行情（直连 TCP，不依赖 HTTP 爬虫）
+ pytdx>=1.72
```

#### 3. `CHANGELOG.md` — 本文件（新增）

### 效果对比

| | 旧（Baostock） | 新（pytdx） |
|---|---|---|
| 协议 | HTTP | TCP socket |
| 速度 | 1-3 小时 | **3.9 分钟** |
| 被封风险 | 高（黑名单） | 极低 |
| 依赖外部域名 | baostock.com | 无（直连 IP） |
| 数据字段 | 开高低收量额涨跌换手 | 开高低收量额 |

### 数据库

- 路径：`cache/market_data.sqlite`（不入 Git，`.gitignore` 已配置）
- 表：`daily_k(code, date, open, high, low, close, volume, amount, pct_chg, turnover)`
- 当前数据：5202 只 A 股，182 万行，2025-01-02 ~ 2026-06-24，240 MB

### 相关文件

- `core/data_fetcher.py:148-213` — `get_kline()` 优先读 `daily_k` 表（毫秒级）
- `core/data_fetcher.py:371-394` — `_bs_get_kline()` Baostock 兜底（P2，当前已废弃）
