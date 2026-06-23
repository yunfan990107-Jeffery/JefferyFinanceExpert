# T1-2 持仓自动取价

**目标**：持仓看板用真实现价替代 P0 的手填/成本价兜底。
**要做什么**
- 在 `app/pages/3_portfolio.py` 中，用 `data_fetcher.get_price(code)` 取每个持仓现价，构造 prices dict 传给 `portfolio.compute_position_metrics`。
- 取价失败时兜底成本价并在界面提示「价格获取失败，用成本价估算」。
**接口契约**：**不改** `portfolio.compute_position_metrics(positions, prices)` 签名（它本就接受 prices dict）；只在页面注入真实 prices。
**交付/验收**：看板显示真实市值/盈亏%；取价失败有兜底与提示；满足 Global DoD。
**依赖**：T1-1、T0-7。
