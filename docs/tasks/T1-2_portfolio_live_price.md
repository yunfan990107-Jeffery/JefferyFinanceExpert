# T1-2 持仓自动取价

**目标**：持仓看板用真实现价替代 P0 的手填/成本价兜底。
**要做什么**
- 在 `app/pages/3_portfolio.py` 中，用 `data_fetcher.get_price(code)` 取每个持仓现价，构造 prices dict 传给 `portfolio.compute_position_metrics`。
- 取价失败时兜底成本价并在界面提示「价格获取失败，用成本价估算」。
**接口契约**：**不改** `portfolio.compute_position_metrics(positions, prices)` 签名（它本就接受 prices dict）；只在页面注入真实 prices。
**交付/验收**：看板显示真实市值/盈亏%；取价失败有兜底与提示；满足 Global DoD。
**依赖**：T1-1、T0-7。

---

## ✅ 完成记录
- **任务**：T1-2 持仓自动取价
- **状态**：已完成
- **完成日期 / 负责 agent**：2026-06-23 / ZCode
- **实现摘要**：
  1. `app/pages/3_portfolio.py` 导入 `data_fetcher`
  2. 遍历持仓逐只调用 `data_fetcher.get_price(code)` 取现价，构造 prices dict
  3. 取价成功用真实现价，失败兜底成本价并在页面显示警告提示
  4. 未改 `portfolio.compute_position_metrics(positions, prices)` 签名
- **改动文件**：
  - 修改：`app/pages/3_portfolio.py`（导入 data_fetcher + 真实现价接入）
- **接口变更**：无
- **新增依赖 / 配置**：无（复用 T1-1 的 akshare）
- **测试**：`pytest -q` → **22 passed**
- **自验收报告**：

  | 验收项 | 验证方式 | 证据 | 通过 |
  |---|---|---|---|
  | 看板显示真实市值/盈亏% | `data_fetcher.get_price` 接入 prices dict → `compute_position_metrics` | 网络可用时取真实现价计算；网络不可用时兜底成本价 | ✅ |
  | 取价失败有兜底与提示 | 页面逻辑：`if price is None → fallback + st.warning` | 失败标的被收集到 `fetch_failures`，页面显示警告 | ✅ |
  | 未改 compute_position_metrics 签名 | 检查 | 仍传 `(positions, prices)` | ✅ |
  | pytest -q 全绿 | `pytest -q` | 22 passed | ✅ |

- **数据来源**：现价取自 AkShare（东方财富等公开数据源）。
- **已知限制 / 遗留 TODO**：
  - 当前网络环境限制 AkShare 外连，完整功能需在有网络访问的环境验证
  - 逐只取价（N 次 API 调用），若持仓数多可优化为批量取全市场行情再过滤（P2）
- **解锁的下游任务**：无（叶子任务）
