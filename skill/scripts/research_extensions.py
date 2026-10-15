"""Original derived trends and explicit coverage, never invent missing breadth."""
import math,statistics
from datetime import date
from market_gates import assess

def extend(assets,market,previous=None):
 cutoff=assets.get('targetSession');date.fromisoformat(cutoff)
 trends=[];matrix=[]
 for r in assets.get('records',[]):
  h=r.get('history',[]);points=[];peak=None;returns=[];prior=None;seen=set();base=None
  for x in h:
   t=x['date'];v=x['value'];date.fromisoformat(t)
   if t>cutoff:continue
   if t in seen or (seen and t<=max(seen)) or isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:raise ValueError('invalid ordered positive history')
   seen.add(t);peak=max(peak or v,v);base=v if base is None else base
   if prior is not None:returns.append(v/prior-1)
   points.append({'date':t,'relative':v/base*100,'drawdown':v/peak-1,'vol20':statistics.stdev(returns[-20:])*math.sqrt(252) if len(returns)>=20 else None});prior=v
  if r.get('kind') not in ('rate','yield') and len(points)>1:trends.append({'id':r['id'],'name':r.get('name',r['id']),'points':points,'basis':'first valid record = 100; price/NAV, not total return; 20-record sample volatility annualised at sqrt(252)'})
  day=r.get('date');fresh='missing' if not day else ('future-rejected' if day>cutoff else 'same-date' if day==cutoff else 'older-observation')
  matrix.append({'id':r['id'],'name':r.get('name',r['id']),'assetClass':r.get('assetClass'),'status':r.get('status','unknown'),'date':day,'freshness':fresh,'calendarLagDays':(date.fromisoformat(cutoff)-date.fromisoformat(day)).days if day else None,'historyCount':len(points),'historyStart':points[0]['date'] if points else None,'historyEnd':points[-1]['date'] if points else None,'requestedHistoryRecords':r.get('requestedHistoryRecords'),'historyShortfall':r.get('historyShortfall'),'region':r.get('region'),'underlyingRegion':r.get('underlyingRegion'),'sourceUrl':r.get('sourceUrl'),'tier':r.get('tier'),'note':r.get('basis','')})
 gates=assess(market,cutoff)['gates'];b=market.get('breadthHistory',[]);ex=market.get('exitHistory',[])
 checks=[{'item':'沪深北同日成交','ready':gates['wholeMarketTurnover']['status']=='conditional','reason':'需三地同日A股统计；不能用沪深替代沪深北'}, {'item':'连续股票广度','ready':gates['continuousBreadth']['status']=='conditional','reason':'需完整声明股票池、连续日历和逐股记录；所选股指不替代股票广度'}, {'item':'全A退出状态','ready':gates['exitPressure']['status']=='conditional' and market.get('exitScope')=='allA','reason':'需同日停牌、实际跌停价及股票池覆盖'}, {'item':'个人资产负债','ready':False,'reason':'仅本地填写；不从行情推算个人财富'}, {'item':'ETF折溢价及赎回','ready':bool(market.get('liquidityObservations')),'reason':'需同日价格/公布净值、币种及赎回合同，不能用估值替代公布净值'}]
 changes=[];prior_date=None
 if previous:
  prior_date=previous.get('asOf')
  if not prior_date or prior_date>=cutoff:raise ValueError('previous research must have earlier asOf')
  old={r['id']:r for r in previous.get('rows',[])}
  for r in assets.get('records',[]):
   priorrow=old.get(r['id'])
   if priorrow and priorrow.get('date')!=r.get('date'):changes.append({'id':r['id'],'before':priorrow.get('date'),'after':r.get('date'),'meaning':'资料日期推进；不等于风险下降'})
 return {'trends':trends,'coverageMatrix':matrix,'readiness':checks,'breadthHistory':b if gates['continuousBreadth']['status']=='conditional' else [],'breadthScope':market.get('breadthScope','unknown'),'breadthReasons':gates['continuousBreadth']['reasons'],'groupBasis':market.get('groupBasis'),'exitHistory':ex if gates['exitPressure']['status']=='conditional' else [],'exitReasons':gates['exitPressure']['reasons'],'volumeHistory':[{'date':r['date'],'value':r['turnover']} for r in market.get('sse',[]) if r['date']<=cutoff],'previousAsOf':prior_date,'previousTitle':previous.get('title') if previous else None,'changes':changes,'previousAvailable':bool(previous),'changeLimits':'rolling windows change endpoints; return differences are not holding-period PnL or risk score changes'}
