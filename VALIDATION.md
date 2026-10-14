# 交付核验

本地核对：2026-10-15。78项 Python 测试、16项页面数据门槛测试。远端覆盖 Windows/Linux 与 Python 3.10/3.12，实际状态以 GitHub Actions 为准。

独立使用：将Skill复制到临时目录，运行基础情景、进阶情景与全资产清单，无其他仓库或作者缓存、无第三方运行依赖。三个示例均为人工构造，不能用于市场结论。

测试覆盖复利与回撤、现金未知值、共同冲击、局部凸性边界、清单遗漏、负债重复、金额溢出、日期错配、股票池变化、交易日缺口、计数分母、覆盖不足、更新失败保留旧日期、报告禁止覆盖与来源链接注入。

可复现：`python -m unittest discover -s tests`；`node tests/market-js.cjs`。冷启动记录（本机单次，不代表数据采集吞吐或实际行情性能）：

[
  {
    "example": "scenario.json",
    "seconds": 0.0809,
    "status": "passed"
  },
  {
    "example": "advanced-scenarios.json",
    "seconds": 0.0757,
    "status": "passed"
  },
  {
    "example": "asset-ledger.json",
    "seconds": 0.0752,
    "status": "passed"
  }
]

市场摘要截至2026-10-14；北市覆盖、连续广度与退出压力仍有资料缺口。网页和计算器不会把缺失认证为安全。
