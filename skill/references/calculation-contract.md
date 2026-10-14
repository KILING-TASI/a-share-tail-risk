# 条件算术与边界

在Skill根目录运行 `python scripts/risk_math.py --input examples/scenario.json`。Python3.10+标准库即可，不联网、不取行情。输入为JSON对象，需非空basis说明合成或来源与单位。模块按需提供。

- recovery：drawdown为0至1的损失比例。回本涨幅=d/(1-d)。损失100%时不能靠剩余本金回本，结果为null并说明，不输出无限值。
- limitPath：dailyDrop为声明比例（0至小于1），days为1至1000整数。累计损失=1−(1−dailyDrop)^days。只是同幅度复合跌幅，未处理价位舍入、板块特殊规则、停牌、交易日历或真实成交。不得把示例10%当现行通用规则。
- portfolio：仅支持unleveredLinear=true，cashWeight与positions权重合计1；每项id唯一、weight为0至1、shock为至少−1的有限数。shock=−1表示声明永久全损；明确给出cashShock，未知现金风险不补零。组合收益=cashWeight×cashShock＋各weight×shock，期末相对价值=1＋收益；反弹回本幅度只在价值低于1时计算。不代表价格路径、退出现金、执行成本、融资、衍生工具或破产概率。

未知参数不补值，缺字段/非法类型/非有限数返回失败，至少一个模块。sourceVerified始终false。负债或非线性持仓用有依据的单独模型；不用此脚本当最大可能损失估计。

包内案例为原创合成：80%现金假设价值不变、20%股票假设全损，得到组合损失20%、回本需25%。假设不是推荐仓位，也不证明剩余资产可随时变现。

## 新增模块

- compoundPath：returns为1至10000个至少−1的等额期间收益，明确无外部资金/费用。输出算术平均、几何平均、声明路径最大回撤和终值。100%全损后财富保持0，数值下溢报错而非认证全损。不是实际生存或概率模型。
- cashConstraints：unit=CNY、snapshotValuesAfterPriorPayments=true；snapshots包含严格递增ISO日期及availableCash、dueCash、reserveFloor、debt、eligibleCollateral、requiredRatio。金额非负，未知用null。现金余量=可用现金−当期到期现金义务−保留资金；担保品/负债与声明阈值比较。快照已反映此前付款，本模块不做现金结转。任何未知必要字段保留unknown；达标不认证合同/强平或生存。
- jointShocks：base含unleveredLinear=true、cashWeight与positions（id/weight）；scenarios各含唯一id、cashShock及shocks字典，必须覆盖全部基础持仓，权重合计1。列各联合情景和最差声明收益，不估计概率/相关性，不把情景相加。
- localResponse：axis、axisUnit、payoffUnit声明同一范围/期间；points恰有3个递增shock，各含grossPayoff与非负cost。absoluteSlopeTolerance需显式给非负绝对斜率差容差。比较成本后相邻斜率，输出sampled-convex/concave/linear-within-tolerance。仅样本局部形状，不认证完整凸性、概率分布或反脆弱机制。

新增模块的合成示例见examples/advanced-scenarios.json。任何输入上的来源真实性、现金可用性、合同阈值和执行都需另行取证。
