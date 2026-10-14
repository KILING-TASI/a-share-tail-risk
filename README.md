# A股尾部风险研究

用市场数据和持仓情景，识别不能承受的损失、退出约束与证据缺口。研究框架参考塔勒布《随机漫步的傻瓜》《黑天鹅》《反脆弱》《非对称风险》，以中国A股制度组织原创分析。

[打开市场观察看板](https://kiling-tasi.github.io/a-share-tail-risk/) · [查看 Skill](skill/SKILL.md) · [数据接入说明](DATA.md) · [数据源分工](SOURCES.md)

## 能回答什么

- 高胜率策略是否隐藏少数大亏，业绩是否受幸存者偏差影响。
- 同时下跌、连续跌停或现金需求上升时，持仓可能遇到什么约束。
- 指数、成交和广度观察覆盖哪些市场，证据是否足以支持当前判断。

不能预测黑天鹅、认证牛熊拐点或保证退出安全。历史最大回撤不是最大可能损失；压力情景不等于发生概率。

## 单独安装 Skill

下载当前 Release 的 `a-share-tail-risk.zip`，解压后把其中 `a-share-tail-risk` 文件夹放入自己的 Skills 目录。也可直接复制本仓库 `skill` 文件夹并改名为 `a-share-tail-risk`。不依赖作者缓存或其他仓库。自然语言示例：

> 用 a-share-tail-risk 检查我的组合：持有三只股票，资金两个月后要用，没有融资。先说明需要哪些持仓数据，再分析共同下跌和无法及时卖出的风险。

基本分析只需能读取 Skill 的助手。复算脚本需 Python 3.10 或以上，不需要第三方依赖：

```sh
python skill/scripts/risk_math.py --help
```

## 市场看板

公开页面附2026-10-14冻结的官方成交和估值统计摘要，明确停止全A综合判断；不是实时页面，不附数据商行情。加载自己有权使用的 JSON 后，本地展示覆盖、连续广度、上海成交历史和退出压力。文件不上传。请核对目标日期确为已完成交易日。`examples/synthetic-contract.json` 是人工测试数据，不能用于市场判断。

```sh
python tools/render_dashboard.py --input examples/empty-market.json --session 2026-10-14 --output local-view.html
python tools/update_market.py --input examples/empty-market.json --session 2026-10-14 --output local-snapshots/20261014
```

更新器尝试官方市场统计；深市文件缺少内部日期时保留“请求日期”状态，不能仅凭请求参数认定日期正确。北交所访问失败、连续广度缺历史、退出记录不足均保留缺口。不会自动抓取禁止批量采集的数据商网站。更新目录与报告禁止覆盖，以保留冻结结果。

## 验证与边界

```sh
python -m unittest discover -s tests
node tests/market-js.cjs
```

Python 3.10+；浏览器需支持本地文件读取、SVG 和现代 JavaScript。离线页面无外部脚本依赖。自动测试核验计算和数据门槛，不能替代真实来源核验、完整盘口成交模拟或许可审核。

原创代码 MIT。第三方文本、行情、公告与书籍保持各自权利范围；链接不代表可转载。没有合法授权的数据不纳入公开包。详见 [许可边界](THIRD_PARTY_NOTICES.md)。
