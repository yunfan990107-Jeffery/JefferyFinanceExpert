# 变更日志（CHANGELOG）

> 面向 AI agent 的可读变更记录。每完成一项重要改动，在顶部新增一节。
> 人类可读的简要记录见 `docs/DEVLOG.md`。

---

## [2026-06-25] 概念板块数据库 + API

### 背景

项目需要板块资金流向、股票归属板块、板块 K 线、板块成分股查询能力。

### 新增文件

- **`scripts/build_concept_db.py`**（新建）
  - 从同花顺 `q.10jqka.com.cn` 爬取 361 个概念板块
  - 概念列表：解析 `q.10jqka.com.cn/gn/` HTML
  - 成分股：AJAX 请求 `q.10jqka.com.cn/gn/detail/order/desc/page/N/ajax/1/code/{code}/`，自动分页
  - 概念 K 线：`ak.stock_board_concept_index_ths()`，同花顺源
  - 资金流向：`ak.stock_fund_flow_concept()`，同花顺源（`data.10jqka.com.cn`）

### 修改文件

- **`core/data_fetcher.py`**：新增 4 个查询接口
  - `get_stock_concepts(code)` — 股票所属概念列表
  - `get_concept_stocks(concept_code)` — 概念成分股列表
  - `get_concept_kline(concept_code, days)` — 概念板块 K 线
  - `get_concept_fund_flow(concept_code, limit)` — 概念资金流向

- **`api/main.py`**：新增 4 个 REST 端点
  - `GET /api/concept/stock/{code}` — 股票概念归属
  - `GET /api/concept/{code}/stocks` — 概念成分股
  - `GET /api/concept/{code}/kline?days=60` — 概念 K 线
  - `GET /api/concept/fund_flow?concept_code=&limit=30` — 概念资金流

### 数据库

在 `data/market_data.sqlite` 新增 3 张表：

| 表 | 说明 | 数据量 |
|---|---|---|
| `stock_concept` | 股票↔概念映射 | 4375 条，1976 只股票 |
| `concept_kline` | 概念板块 K 线 | 172K 行，2 年 |
| `concept_fund_flow` | 概念资金流向 | 235 条（日频） |

### 已知限制

- 部分概念成分股不完整（10jqka 分页限制待排查）
- 平均每只股票 2.2 个概念（偏少，后续可扩充更多概念源）
- 全量构建耗时约 7 分钟

---

## [2026-06-25] Git 远程切换为 SSH + 环境信息

### 背景

本机网络环境下 HTTPS 443 端口无法连接 GitHub（无论是否开 VPN，部分 VPN 节点分流规则不覆盖 443）。经测试 SSH 22 端口在部分 VPN 节点可用。

### 操作

1. 生成 ED25519 SSH 密钥对：`~/.ssh/id_ed25519`
2. 公钥已添加至 GitHub Settings → SSH Keys
3. **remote 已切换为 SSH**：`git@github.com:yunfan990107-Jeffery/JefferyFinanceExpert.git`

### 重要提醒

> ⚠️ **不要将 remote 改回 HTTPS**，否则无法 push。
> 如果 `git push` 失败，检查：
> 1. VPN 是否开启且节点支持 SSH（22 端口）
> 2. `~/.ssh/id_ed25519` 是否存在
> 3. `git remote -v` 确认是 `git@github.com:...` 而非 `https://...`

### 本机环境

| 项 | 值 |
|---|---|
| OS | Windows 11 x64 |
| Shell | Git Bash (MSYS2) |
| Python | 3.13.13 (Miniconda3, 路径 `C:\Users\Jeffery\miniconda3\`) |
| 虚拟环境 | `.venv`（项目根目录） |
| Node | 通过 npx 可用 |
| SSH 密钥 | `~/.ssh/id_ed25519` (ED25519) |
| Git remote | `git@github.com:yunfan990107-Jeffery/JefferyFinanceExpert.git` (SSH) |
| 通达信服务器 | `218.75.126.9:7709` (pytdx 默认) |

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
