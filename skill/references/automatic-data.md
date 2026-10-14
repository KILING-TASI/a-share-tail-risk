# 自动取数与使用

现在可以自动取得所选股票、指数、ETF、公募REITs、基金单位净值，以及黄金现货合约、利率和外汇参考指标。默认清单用于连接验收，可换成自己的代码；不是推荐组合，也不是全市场股票名单。

## 直接使用

单独安装 Skill 后，在 Skill 文件夹中运行：

```sh
python scripts/collect_assets.py --manifest examples/asset-manifest.json --session 2026-10-14 --output outputs/assets-20261014.json
python scripts/render_dashboard.py --input examples/market-empty.json --session 2026-10-14 --assets outputs/assets-20261014.json --output outputs/dashboard-20261014.html
```

打开生成的 HTML 即可查看数据、历史记录、来源、日期及失败提示。不需要其他仓库、作者缓存或第三方 Python 依赖。Windows 原生 HTTPS 用于欧洲央行的证书兼容回退，仍验证证书，绝不关闭 TLS 校验。

完整仓库可用一个命令更新官方市场统计并生成综合看板：

```sh
python tools/refresh_all.py --session 2026-10-14 --output local-snapshots/20261014-v1
```

再次更新使用新目录或文件名；可加 `--previous-assets 旧目录/assets.json` 累积历史并处理失败回退。旧数据标记 `stale-cache`，不冒充刷新成功。已有快照不覆盖。历史数据商前复权版本不混入不同版本旧报价；保留本次版本，不认证历史时点可得性。

## 已接通来源

| 内容 | 来源与口径 | 实际功能 |
|---|---|---|
| 股票、指数、股票/债券/黄金ETF、REITs | 腾讯报价与历史，新浪报价作回退和交叉核验 | 指定代码报价、约120个历史点（来源实际返回为准）；价格指数用点，股票元/股，基金元/份 |
| 公募基金 | 天天基金二手公布单位净值 | 截止日以前约120个净值点；拒绝把盘中估算当净值，不把未复原分红的净值当总收益 |
| 黄金现货合约 | 上海黄金交易所 Au99.99 每日记录 | 指定日期收盘，元/克；不是金饰零售价或其他黄金合约 |
| 利率 | 中国货币网 Shibor | 隔夜利率历史，单位%；不是个人存款报价 |
| 国债 | 中债国债收益率曲线 | 1/3/5/10/30年期限点；保留接口worktime，页面日期冲突或记录较旧时提示，不改写日期 |
| 汇率 | 欧洲央行官方参考汇率 | EUR/CNY及同日交叉换算USD/JPY/GBP对CNY，约90日公布记录；不是中国外汇中间价或银行成交报价 |
| 沪深市场统计 | 上交所每日统计、深交所XLSX与带日期JSON | 沪市核返回日期，深市自动核报告subname日期、亿元单位与A股板块金额 |

参考原始入口：[上金所](https://www.sge.com.cn/sjzx/quotation_daily_new)、[中国货币网](https://www.chinamoney.com.cn/chinese/bkshibor/)、[中债](https://yield.chinabond.com.cn/cbweb-pbc-web/pbc/more?locale=cn_zh)、[ECB数据下载](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)。公开接口没有稳定性保证；失败保留原因，不绕过登录、验证码或访问限制。

公开 GitHub 看板附官方摘要；数据商报价和历史保存在本地自动结果，未经许可不随安装包或公开页面传播。个人资产与账户文件也不上传。当前公开页是冻结展示，最新数据应运行更新命令；它不是浏览器内实时行情终端。

## 连续广度与退出代理指标

具备有权使用的逐股日数据时，可以自动生成观察结果：

```sh
python scripts/build_observations.py --csv daily.csv --metadata pool.json --output observations.json
```

CSV列：`date,code,close,prevClose,volume,status,limitDown`。status仅接受trading/suspended。prevClose需对应当日官方参考价；拆并股、除权等由数据方法核验，不用普通昨日未调整价格替代。limitDown未知留空，不用0补未知；0仅表示已明确无跌停价。

元数据：`expectedSessions`为核验后的有序交易日，`poolCodes`为完整逐日股票清单，`poolId`、`ruleVersion`、`methodVerified:true`和`scope`。scope默认selected，只有有证据支持完整全A才填allA。程序拒绝漏日、漏股、重复代码、非法价格和交易状态。停牌纳入分母并单列，规则限制与零成交可能重叠，不相加。输出可用 `refresh_all.py --observations observations.json` 合入报告。

目前没有取得完整全A历史股票池与逐股状态，因此生成器已经可用，完整市场广度数据尚未齐备；不会用所选16个指标代替全市场。

## 不能用一个报价解决的项目

存款期限与提前支取、理财底层资产与赎回、房地产与非上市股权估值、债务担保和经营现金流，需要合同、原始披露和具体对象。没有资料保持未知。基金估算、黄金ETF价格、国债收益率、房价指数都不能自动替代这些对象的实际价值或可用现金。
