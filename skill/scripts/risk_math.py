# SPDX-License-Identifier: MIT
"""Declared scenario arithmetic; not an execution or ruin probability model."""
import argparse,json,math
from datetime import date
from pathlib import Path
def number(v,name,lo=None,hi=None):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError(name+'必须是有限数字')
    if (lo is not None and v<lo) or (hi is not None and v>hi):raise ValueError(name+'超出范围')
    return float(v)
def recovery(p):
    d=number(p['drawdown'],'drawdown',0,1)
    return dict(requiredGain=None if d==1 else number(d/(1-d),'requiredGain'),recoverableFromRemainingCapital=d<1)
def limit_path(p):
    d=number(p['dailyDrop'],'dailyDrop',0,1);days=p['days']
    if d==1 or isinstance(days,bool) or not isinstance(days,int) or not 1<=days<=1000:raise ValueError('dailyDrop需小于1，days需1至1000整数')
    return dict(compoundedLoss=1-(1-d)**days,executionGuaranteed=False,ruleVerified=False)
def portfolio(p):
    if p.get('unleveredLinear') is not True:raise ValueError('仅支持明确无杠杆线性持仓；融资或衍生品需另建模型')
    cash=number(p['cashWeight'],'cashWeight',0,1);cash_shock=number(p['cashShock'],'cashShock',-1)
    rows=p['positions']
    if not isinstance(rows,list) or len(rows)>10000:raise ValueError('positions需最多10000项列表')
    total=cash;value=cash*cash_shock;ids=set()
    for row in rows:
        key=row['id']
        if not isinstance(key,str) or not key.strip() or key in ids:raise ValueError('持仓id空值或重复')
        ids.add(key);weight=number(row['weight'],'weight',0,1);shock=number(row['shock'],'shock',-1);total+=weight;value+=weight*shock
    if abs(total-1)>1e-9:raise ValueError('现金与持仓权重需合计1，不补隐含现金或融资')
    value=number(value,'computed portfolio return');remaining=number(1+value,'remaining value',0)
    return dict(declaredReturn=value,relativeEndingValue=remaining,recovery=recovery({'drawdown':max(0,-value)}),liquidationCashCertified=False)
def compound_path(p):
    rows=p['returns']
    if not isinstance(rows,list) or not 1<=len(rows)<=10000:raise ValueError('returns需1至10000个声明期间收益')
    values=[number(x,'return',-1) for x in rows];wealth=1.;peak=1.;maxdd=0.;path=[]
    for v in values:
        prior=wealth;wealth=number(wealth*(1+v),'compounded wealth',0)
        if wealth==0 and prior>0 and v> -1:raise ValueError('复合值数值下溢，不能当作实际全损')
        peak=max(peak,wealth);maxdd=max(maxdd,1-wealth/peak);path.append(wealth)
    geometric=-1. if any(v== -1 for v in values) else math.expm1(sum(math.log1p(v) for v in values)/len(values))
    return dict(arithmeticMean=number(sum(values)/len(values),'mean'),geometricMean=number(geometric,'geometric mean'),endingRelativeValue=wealth,maxDrawdownInDeclaredPath=maxdd,relativePath=path,survivalCertified=False,limits='无新增资金、提款、融资和交易成本的声明复合路径；样本回撤不是未来损失上界')
def cash_constraints(p):
    if p.get('snapshotValuesAfterPriorPayments') is not True or p.get('unit')!='CNY':raise ValueError('需明确CNY与已计入此前付款的快照口径')
    rows=p['snapshots']
    if not isinstance(rows,list) or not 1<=len(rows)<=1000:raise ValueError('snapshots需1至1000项')
    result=[];last=None
    for row in rows:
        day=date.fromisoformat(row['date'])
        if last is not None and day<=last:raise ValueError('快照日期需严格递增')
        for key in ('availableCash','dueCash','reserveFloor','debt','eligibleCollateral','requiredRatio'):
            if row.get(key) is not None:number(row[key],key,0)
        last=day;cash=row.get('availableCash');due=row.get('dueCash');reserve=row.get('reserveFloor');status='unknown';headroom=None
        if all(v is not None for v in (cash,due,reserve)):
            headroom=number(number(cash,'availableCash',0)-number(due,'dueCash',0)-number(reserve,'reserveFloor',0),'cash headroom');status='shortfall' if headroom<0 else 'within-declared-cash-floor'
        debt=row.get('debt');collateral=row.get('eligibleCollateral');threshold=row.get('requiredRatio');margin='unknown';ratio=None
        if debt is not None:
            debt=number(debt,'debt',0)
            if debt==0:margin='no-declared-debt'
            elif collateral is not None and threshold is not None:
                ratio=number(number(collateral,'eligibleCollateral',0)/debt,'collateral ratio');margin='below-declared-ratio' if ratio<number(threshold,'requiredRatio',0) else 'within-declared-ratio'
        result.append(dict(date=row['date'],cashStatus=status,cashHeadroom=headroom,collateralStatus=margin,declaredCollateralRatio=ratio))
    return dict(snapshots=result,survivalCertified=False,contractVerified=False,limits='独立日期快照，不模拟现金结转、券商强平执行或担保品真实折算；达标不等于一定存活，未知不当作通过')
def joint_shocks(p):
    base=p['base'];rows=p['scenarios']
    if not isinstance(rows,list) or not 1<=len(rows)<=1000:raise ValueError('scenarios需1至1000项')
    if base.get('unleveredLinear') is not True:raise ValueError('联合冲击只支持明确无杠杆线性持仓')
    ids=[x['id'] for x in base['positions']]
    if len(ids)!=len(set(ids)):raise ValueError('基础持仓id重复')
    results=[];seen=set()
    for row in rows:
        name=row['id']
        if not isinstance(name,str) or not name.strip() or name in seen:raise ValueError('情景id空值或重复')
        seen.add(name)
        if not isinstance(row['shocks'],dict) or set(row['shocks'])!=set(ids):raise ValueError('每个联合情景须覆盖全部且仅有基础持仓，不补未知冲击')
        q=dict(unleveredLinear=True,cashWeight=base['cashWeight'],cashShock=row['cashShock'],positions=[dict(id=x['id'],weight=x['weight'],shock=row['shocks'][x['id']]) for x in base['positions']]);v=portfolio(q)
        results.append(dict(id=name,declaredReturn=v['declaredReturn'],relativeEndingValue=v['relativeEndingValue']))
    return dict(scenarios=results,worstDeclaredReturn=min(x['declaredReturn'] for x in results),probabilityEstimated=False,limits='只比较所列同时冲击；未估相关性、尾部依赖、发生概率或未来最大损失；情景不可相加')
def local_response(p):
    for key in ('axis','axisUnit','payoffUnit'):
        if not isinstance(p.get(key),str) or not p[key].strip():raise ValueError('需声明冲击轴与单位')
    rows=p['points']
    if not isinstance(rows,list) or len(rows)!=3:raise ValueError('仅比较三个严格递增冲击点')
    tol=number(p['absoluteSlopeTolerance'],'absoluteSlopeTolerance',0);xs=[];ys=[]
    for row in rows:
        xs.append(number(row['shock'],'shock'));ys.append(number(number(row['grossPayoff'],'grossPayoff')-number(row['cost'],'cost',0),'netPayoff'))
    if not xs[0]<xs[1]<xs[2]:raise ValueError('冲击点需严格递增')
    left=number((ys[1]-ys[0])/(xs[1]-xs[0]),'left slope');right=number((ys[2]-ys[1])/(xs[2]-xs[1]),'right slope');delta=number(right-left,'slope change')
    shape='sampled-convex' if delta>tol else 'sampled-concave' if delta< -tol else 'sampled-linear-within-tolerance'
    return dict(netPayoffs=ys,leftSlope=left,rightSlope=right,slopeChange=delta,sampledShape=shape,antifragilityCertified=False,limits='仅三个点的成本后局部斜率差；需同期限/范围、执行与资金约束，不能证明完整凸性或对所有扰动反脆弱')
def review(data):
    if not isinstance(data,dict) or not isinstance(data.get('basis'),str) or not data['basis'].strip():raise ValueError('需JSON对象和非空basis说明假设、来源及单位')
    results={}
    for name,fn in [('recovery',recovery),('limitPath',limit_path),('portfolio',portfolio),('compoundPath',compound_path),('cashConstraints',cash_constraints),('jointShocks',joint_shocks),('localResponse',local_response)]:
        if name in data:results[name]=fn(data[name])
    if not results:raise ValueError('至少提供一个计算模块')
    return dict(status='declared-scenario-arithmetic',sourceVerified=False,probabilityEstimated=False,basis=data['basis'],results=results,limits=['不取行情、不认证规则或成交','非最大损失、融资强平或破产概率模型','情景权重不是推荐仓位'])
def main():
    ap=argparse.ArgumentParser(description='A股风险声明情景算术');ap.add_argument('--input',required=True);args=ap.parse_args()
    try:
        def reject(v):raise ValueError('禁止非有限JSON常量')
        data=json.loads(Path(args.input).read_text(encoding='utf-8-sig'),parse_constant=reject);print(json.dumps(review(data),ensure_ascii=False,indent=2,allow_nan=False));return 0
    except (ValueError,KeyError,TypeError,OSError,OverflowError,AttributeError) as e:print('计算失败：'+str(e));return 1
if __name__=='__main__':raise SystemExit(main())
