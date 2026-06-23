# 开发日志（DEVLOG）

> 每完成一张任务卡，在本文件**顶部**加一行：`- [YYYY-MM-DD] T0-X 完成 — 摘要（agent 名）`
> 详细完成记录写在对应 `docs/tasks/T0-X.md` 末尾的「✅ 完成记录」。

- [2026-06-23] 架构师加固 — 补 tools/registry/stock_research/llm_client/intel 单测(测试 33→57)；加 core/obs.py 调用日志并接入 llm_client；**修 2 个真 bug**：stock_research._build_data_summary 未定义变量 days(kline 非空即崩)、intel._classify_news 摘要解析取错段致摘要恒空（架构师）
- [2026-06-23] P2-1/P2-2 完成 — 绩效归因 attribution()+7单测 + Baostock兜底/质量校验/缓存健壮（ZCode）
- [2026-06-23] T2-1/T2-2 完成 — Agent 架构扩展性重构（配置化/tool registry/function-calling/可配置流水线）+ 报告推送脚本（ZCode）
- [2026-06-23] T1-7/T1-5/T1-6 完成 — 金融教练角色 + 信息筛选 intel.py + 认知档案月度校准（ZCode）
- [2026-06-23] T1-3 完成 — 个股深度研究流程编排（取数→草稿→反方→风险→汇总→入库），飞书新建研究库表（ZCode）
- [2026-06-23] T1-4 完成 — 拆分反方/风险为独立角色（devil_advocate + risk_control），quality_review 裁为总编（ZCode）
- [2026-06-23] T1-2 完成 — 持仓看板接入 data_fetcher 真实现价，失败兜底成本价+提示（ZCode）
- [2026-06-23] T1-1 完成 — 数据层 AkShare + SQLite 缓存，4 个取数函数 + 8 个单测（ZCode）
- [2026-06-23] 架构师维护 — 接通 DeepSeek LLM(.env)；llm_client 增通用 chat()/load_role() 共享入口；修复 feishu_client Windows UTF-8 解码 bug(GBK 致 stdout=None)；加 pytest.ini 限定 testpaths；文档同步 P0 完成+LLM 用法（架构师）
- [2026-06-23] T0-6 完成 — 复盘中心完整闭环：到期判断→Brier→LLM质量审查→写回飞书，P0 全部交付 🎉（ZCode）
- [2026-06-23] T0-8 完成 — 质量审查角色对齐 + 贵州茅台示范个股深度研究，存入飞书 Wiki（ZCode）
- [2026-06-23] T0-7 完成 — 持仓看板接 FeishuClient，录入+列表+集中度提示闭环（ZCode）
- [2026-06-23] T0-5 完成 — 记判断页接 FeishuClient，去掉 NotImplementedError 占位，端到端验证通过（ZCode）
- [2026-06-23] T0-3 完成 — 实现 FeishuClient（lark-cli subprocess 封装），add/update/list/get_due 全部可用，7 个集成测试全绿（ZCode）
- [2026-06-23] T0-2 完成 — 飞书建表 6 张（judgments/portfolio/tasks/decisions/risk_reviews/intel），字段对齐 .env 已填（ZCode）
- [2026-06-23] T0-1 完成 — 仓库骨架、core 接口契约、Streamlit 三页、任务卡（架构师）
- [2026-06-23] T0-4 完成 — calibration 纯逻辑实现 + 单元测试（架构师）
