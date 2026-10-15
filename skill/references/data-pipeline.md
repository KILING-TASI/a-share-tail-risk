# 多地区采集与严格匹配

## 实际采集范围

资产清单 `examples/asset-manifest.json` 可设置 `historyRecords`（61—5000，请求点数，来源可能不足）、`startDate`（用于汇率及Shibor请求起点）、`longFxHistory`。证券与基金按记录点数请求，不保证覆盖startDate；每条记录保留实际区间。境内上市的跨境ETF保留上市区域与底层地区，不冒充境外直接报价。

运行：

```sh
python scripts/collect_assets.py --manifest examples/asset-manifest.json --session 2026-10-14 --output outputs/assets.json
python scripts/collect_context.py --manifest examples/context-manifest.json --session 2026-10-14 --output outputs/context.json
python scripts/render_dashboard.py --input examples/market-empty.json --assets outputs/assets.json --context outputs/context.json --session 2026-10-14 --output outputs/dashboard.html
```

以上均为新文件，不覆盖旧报告。数据源变化或缺失不会导致旧日期被重标。暂时性429/5xx与传输异常最多3次；401/403不重试。Shibor长区间无值时尝试近120天，保留原失败和实际范围。重跑不是补齐全部历史的证明。新返回的历史序列保持本次版本，不被旧缓存截回252点，也不拼接不同复权/净值版本。

宏观清单覆盖中国内地、中国香港、美国、日本、德国、英国、印度、巴西；WDI指标为GDP增速、CPI通胀、ILO模型失业率、制造业增加值/GDP、出口/GDP及广义货币/GDP。`startYear/endYear`分别控制年度请求范围；不请求尚未结束年度的完整数值。缺失值保持缺失，报告每地区每指标有效/缺失年份。

世界银行是该数据集发布方，部分底层数据来自各国统计机构、ILO等，并非所有指标都直接采自各国一手网站。数据源：[WDI API说明](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392)。国内省级接口403保留失败，不绕过访问限制。国内月度与省市、微观财报及公告原文需要分别接入核验，不用年度全国值或跨境ETF替代。

## 匹配器

`data_matcher.py --input 文件.json`：输入left/right规范记录、mode、可选cutoff与pointInTime。规范记录需 `entityId,metric,region,frequency,period,unit,basis,sourceUrl,value`，币种不适用时currency为null；真实发布日期用带时区availableAt，未知为null。`version`保留修订版本，shareClass保留份额类别。

- same-series：标的、份额、指标、频率、期间、单位、币种和口径一致。
- cross-region：相同指标、频率、期间、单位、币种和口径可跨地区比较。
- premium：market_price与published_unit_nav须为同一标的/份额、同期间同币种同单位；不接受估算净值。basis在这里表达共同单位计价基础，两个不同metric保留价格与净值的区别。同日不证明同一时刻或可套利。
- 5/20/60期研究用match_window匹配基准真实起止日，缺端点不取邻日、不前填。收益是各自计价币种的价格/净值变化，不自动外汇转换、不等于含息总收益。
- pointInTime=true须有带时区的真实公布时间，按cutoff上海时区日末检查；统计期间、抓取时间、接口更新日都不能替代首次公布时间。WDI当前版本的availableAt为空，拒绝历史时点认证。
- 同一标识、期间、版本的冲突值隔离，完全重复去重，不自动偏向某一来源；不同版本保留，不静默覆盖。

## 完整股票池与退出代理

`build_observations.py`兼容原CSV，并可加turnover成交额。元数据groups按代码声明exchange/size，groupBasis说明分组依据；不将当前规模分类冒充历史点时分类。

新增交易证券上涨占比、中位数涨跌幅、MA20/MA60以上占比、突破此前20期新高/新低，分别显示有效样本数。用每日close/当日prevClose链式构造路径，需核参考价、除权与公司行动。停牌单列并排除交易证券分母。成交萎缩=当日成交额小于此前20期均值50%；缺数据不记0。跌停价须逐证券逐日输入，不统一套10%。

完整全A资料没有取得前，页面拒绝全A状态判断。局部源可用不代表完整数据源齐备。

## 四个本地计算器

```sh
python scripts/risk_lab.py --input examples/cashflow-input.json
python scripts/risk_lab.py --input examples/fragility-input.json
python scripts/risk_lab.py --input examples/barbell-input.json
python scripts/risk_lab.py --input examples/protection-input.json
```

示例均为人工情景，非市场事实。金额事先统一换算成人民币。

现金流按月末核算收入中断、必要开支、债务本息和延后卖出净到账；后期到账不抹去先前缺口，不覆盖月中路径。fragility将账户权益、债务、担保估值折扣、合同维护倍数和账户外现金分开；追保是额外现金占用，不重复记作价格损失；没有真实融资清算路径，不推算强平价。barbell检查储备减值、不可用部分、风险端声明损失上限与成本预算；上限未核验则预算余量未知。protection计权利金、续持、交易费用、现金机会成本和情景损耗，比较无回款与声明冲击；不算期望收益，不为卖方义务定价。

报告支持前一期研究摘要对照（--previous-research），前一期必须早于本期；没有之前版本不制造历史判断。浏览器可导出研究摘要或单独导出个人情景；二者分开，参数修改后原计算立即失效。

## 固定组件、原始响应与离线重放

匹配器、WDI解析及响应归档权威实现归cn-data-adapters；当前Skill携带经登记的固定副本，无跨仓运行依赖。采集CLI会在输出文件旁生成`.sources`新目录，保存原始响应、失败和SHA256。目录属于本地研究资料，不随公开安装包发布。

```sh
python scripts/collect_context.py --manifest examples/context-manifest.json --session 2026-10-14 --output outputs/context-new.json
python scripts/collect_context.py --manifest examples/context-manifest.json --session 2026-10-14 --replay-archive outputs/context-new.json.sources --output outputs/context-replay.json
```

collect_assets.py支持同样的--replay-archive。重放不联网，不以新时间覆盖原取得时间，单列replayedAt；修改响应、缺文件或无请求记录时拒绝/保留失败。archive完成只表示捕获流程结束，不代表每个来源成功。数据仓可选tail-risk-import将结果转为cn-research-observations/1.0；未安装数据仓仍能独立研究和生成看板。
