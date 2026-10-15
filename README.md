# A股尾部风险研究

用市场数据和持仓情景，识别不能承受的损失、退出约束与证据缺口。范围包括家庭和企业的现金、存款、债券、理财、房地产、黄金、外汇、经营资产及负债。研究框架参考塔勒布《随机漫步的傻瓜》《黑天鹅》《反脆弱》《非对称风险》，以中国A股制度组织原创分析。

[打开市场观察看板](https://kiling-tasi.github.io/a-share-tail-risk/) · [查看 Skill](skill/SKILL.md) · [数据接入说明](DATA.md) · [数据源分工](SOURCES.md) · [自动取数](AUTO_DATA.md)

## 能回答什么

- 高胜率策略是否隐藏少数大亏，业绩是否受幸存者偏差影响。
- 同时下跌、连续跌停或现金需求上升时，持仓可能遇到什么约束。
- 指数、成交和广度观察覆盖哪些市场，证据是否足以支持当前判断。

不能预测黑天鹅、认证牛熊拐点或保证退出安全。历史最大回撤不是最大可能损失；压力情景不等于发生概率。

## 单独安装 Skill

下载当前 Release 的 `a-share-tail-risk.zip`，解压后把其中 `a-share-tail-risk` 文件夹放入自己的 Skills 目录。也可直接复制本仓库 `skill` 文件夹并改名为 `a-share-tail-risk`。不依赖作者缓存或其他仓库。自然语言示例：

> 用 a-share-tail-risk 检查我的组合：持有三只股票，资金两个月后要用，没有融资。先说明需要哪些持仓数据，再分析共同下跌和无法及时卖出的风险。

基本分析只需能读取 Skill 的助手。自动取数、复算与本地看板需 Python 3.10 或以上，不需要第三方 Python 依赖：

```sh
python skill/scripts/risk_math.py --input skill/examples/scenario.json
python skill/scripts/asset_ledger.py --input skill/examples/asset-ledger.json
```

## 自动取得数据

股票、指数、ETF、REITs、基金净值、黄金合约、国债收益率、Shibor和汇率已接通自动来源。单独Skill可以取数并生成HTML；完整仓库可以一条命令联动官方统计、资产数据和看板：

```sh
python tools/refresh_all.py --session 2026-10-14 --output local-snapshots/20261014-v1
```

默认代码是连接验收清单，可以替换。它不是全市场池；存款、理财、房产和个人负债需具体合同或估值资料。[操作和覆盖说明](AUTO_DATA.md)。

## 研究看板

首页先给所选样本的变化、分歧、风险机制与观察条件，展示相同起止日的5/20/60期变化、窗口回撤和共同波动。默认清单已扩至43条证券、基金与官方参考记录；新增香港、德国、日本市场的境内上市ETF样本。证券/基金请求750点历史，汇率从2016年起；以实际取得范围为准。公开页展示原创计算摘要，不分发数据商原始序列。

首页新增价格路径、回撤、滚动波动率、连续广度与退出缺口、数据覆盖矩阵、多地区年度宏观对照，以及个人现金流、脆弱性曲线、杠铃两端和保护成本工具。所有个人参数仅本地计算，不自动保存或上传。

多地区宏观现有8个国家或地区、6类年度指标，2010—2025年请求范围实际取得737条观察，47/48地区指标组合有数据。年度数值为最新修订版，不能当作历史时点已知数据。国内省市、完整全A逐股历史与发行人财务尚有缺口，不宣称全部接通。

## 市场看板

看板还支持本地全资产清单与现金压力复算，并列出杠铃、有限成本选择权、可逆试错等安排的适用边界。

公开页面附2026-10-14冻结的官方成交和估值统计摘要，明确停止全A综合判断；不是实时页面，不附数据商行情。加载自己有权使用的 JSON 后，本地展示覆盖、连续广度、上海成交历史和退出压力。文件不上传。请核对目标日期确为已完成交易日。`examples/synthetic-contract.json` 是人工测试数据，不能用于市场判断。

```sh
python tools/render_dashboard.py --input examples/empty-market.json --session 2026-10-14 --output local-view.html
python tools/update_market.py --input examples/empty-market.json --session 2026-10-14 --output local-snapshots/20261014
```

更新器尝试官方市场统计；深市XLSX与官方JSON报告的日期、A股范围和金额自动交叉核验；不能仅凭请求参数认定日期正确。北交所访问失败、连续广度缺历史、退出记录不足均保留缺口。不会自动抓取禁止批量采集的数据商网站。更新目录与报告禁止覆盖，以保留冻结结果。

## 验证与边界

```sh
python -m unittest discover -s tests
node tests/market-js.cjs
node tests/research-ui.cjs
node tests/advanced-ui.cjs
```

Python 3.10+；浏览器需支持本地文件读取、SVG 和现代 JavaScript。离线页面无外部脚本依赖。自动测试核验计算和数据门槛，不能替代真实来源核验、完整盘口成交模拟或许可审核。

原创代码 MIT。第三方文本、行情、公告与书籍保持各自权利范围；链接不代表可转载。没有合法授权的数据不纳入公开包。详见 [许可边界](THIRD_PARTY_NOTICES.md)。

## 公开底稿验收

[覆盖登记](PUBLIC_VALIDATION.json)区分公开事实、混合教学与尚缺样本。运行 `python tools/verify_public_validation.py --run-checks --output reports/public-validation-v1.json` 可核对冻结文本与已登记反例；重复运行使用新文件。通过不表示重新认证原文或真实市场效果，未取得的样本仍列为缺口。
