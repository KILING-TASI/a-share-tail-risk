# 数据接入与判断门槛

输入格式见 `examples/empty-market.json` 和 `examples/synthetic-contract.json`。后者所有数字均为人工构造，只有测试用途。

`asOf` 为资料截止日，`retrievedAt` 为实际获取时间；不能互相替代。目标交易日独立选择，加载旧快照不改变它。

- `coverage` 按 SSE、SZSE、BSE 分别填写。成交额单位 `CNY-100m`（亿元），范围 `A-share`。只有同日、已核验范围的三个市场都齐全，才能展示全A合计。`verified-snapshot` 是使用者声明，需要保存来源证据。
- `breadthHistory` 每行包含 `date/up/flat/down/total/poolId/methodVerified`。涨、平、跌之和必须等于分母。至少五个观察日，股票池标识一致，`expectedSessions` 与记录日期逐项一致；这份日历也需使用者核验。不得跨漏日画成连续趋势。
- `exitPressure` 包含日期、股票池、规则版本、方法核验、应覆盖数与已覆盖数，以及 `downLimit/suspended/zeroVolumeDown`。未知填 null，不填0。三项可能重叠，不能相加；只能表示指定规则下观察到的代理指标。
- `sse` 包含 date、turnover、turnoverA、turnoverStar、peA、peStar、turnoverRateA、turnoverRateStar；`csi300` 包含 date、close。至少六个点、结束日与目标日相同才满足短窗口描述门槛。不得以不足六个点推断五个交易区间收益。
- `sources` 保存 name、http(s) url。建议另存数据许可、原始文件摘要、取得时间与核验凭据。来源标签和链接不是真实性认证。

数据商来源须有使用和转载许可。公开报告另行检查公开传播权。官方统计入口可能改变或拒绝访问；更新器保存失败原因，保留旧资料日期，不绕过访问限制。更新快照目录应单独保存，不提交原始或用户数据至 GitHub。

## 更新与复现

每次指定新输出目录；快照与 update-log.json 一起保存。深市优先用官方JSON报告日期及A股金额自动核对XLSX；必要时仍支持 `--sz-date-proof` 人工独立凭据。报告指定新文件名。参数、来源版本和冻结文件保持对应。

公开版附官方参考序列；数据商历史行情自动取到本地，连续广度和退出压力尚无完整默认全A数据源。功能接通不等于当前市场数据已齐备。空输入、缺市场、日期不符或覆盖不完整时拒绝相关判断。
