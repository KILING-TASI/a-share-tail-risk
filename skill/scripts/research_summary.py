"""Dated original descriptive statistics, not a regime predictor."""
import math,statistics

def summarize(d,market=None):
 records=d.get('records',[]);byid={r['id']:r for r in records};base=byid.get('sh000300',{}).get('history',[]);days=[r['date'] for r in base];rows=[]
 for r in records:
  h=r.get('history',[]);values={x['date']:x['value'] for x in h};row={'id':r['id'],'name':r.get('name',r['id']),'assetClass':r['assetClass'],'date':r.get('date'),'source':r.get('source',r.get('tier')),'sourceUrl':r.get('sourceUrl'),'basis':r.get('historyBasis',r.get('basis','')),'changes':{}}
  for n in (5,20,60):
   if r.get('kind') not in ('rate','yield') and len(days)>n and days[-1] in values and days[-n-1] in values and values[days[-n-1]]>0:row['changes'][str(n)]=values[days[-1]]/values[days[-n-1]]-1
   else:row['changes'][str(n)]=None
  cut=[x for x in h if len(days)>60 and days[-61]<=x['date']<=days[-1]];peak=None;dd=0
  for x in cut:
   peak=max(peak or x['value'],x['value']);dd=min(dd,x['value']/peak-1)
  row['drawdown60']=dd if r.get('kind') not in ('rate','yield') and len(days)>=61 and all(t in values for t in days[-61:]) else None
  row['curve']=r.get('curve') if r.get('tier')=='primary' else None
  row['level']=r.get('value') if r.get('tier')=='primary' else None;row['unit']=r.get('unit');rows.append(row)
 indices=[r for r in rows if r['id'] in ('sh000300','sh000905','sh000852','sh000688','sz399006') and r['changes']['20'] is not None];negative=sum(r['changes']['20']<0 for r in indices)
 title='股指样本不足，保留市场方向判断' if len(indices)<3 else ('所选股指多数走弱，先检查共同暴露' if negative>len(indices)/2 else ('所选股指多数上行，仍需检查尾部约束' if sum(r['changes']['20']>0 for r in indices)>len(indices)/2 else '所选股指方向分化，继续核对共同暴露'))
 pairs=[]
 for left,right,label in [('sh000300','sh000905','大盘与中盘'),('sh000300','sh518880','股票与黄金ETF'),('sh000300','sh511260','股票与长久期国债ETF'),('sh000300','sh513100','A股与纳指ETF')]:
  a={x['date']:x['value'] for x in byid.get(left,{}).get('history',[])};b={x['date']:x['value'] for x in byid.get(right,{}).get('history',[])};xs=[];ys=[]
  for t0,t1 in zip(days[-61:],days[-60:] if len(days)>=61 else days[1:]):
   if all(t in a and t in b and a[t]>0 and b[t]>0 for t in (t0,t1)):xs.append(a[t1]/a[t0]-1);ys.append(b[t1]/b[t0]-1)
  corr=None
  if len(xs)>=20 and statistics.pstdev(xs)>0 and statistics.pstdev(ys)>0:
   mx=statistics.mean(xs);my=statistics.mean(ys);corr=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
  pairs.append({'label':label,'correlation':corr,'observations':len(xs)})
 market=market or {};coverage=market.get('coverage',{});turnovers=[coverage.get(k,{}) for k in ('SSE','SZSE')];turnover=sum(r['turnover'] for r in turnovers) if all(r.get('status')=='verified-snapshot' and r.get('date')==d.get('targetSession') and r.get('unit')=='CNY-100m' and r.get('securityScope')=='A-share' for r in turnovers) else None
 sse=market.get('sse',[]);volume_change=sse[-1]['turnover']/sse[-2]['turnover']-1 if len(sse)>1 and sse[-1]['date']==d.get('targetSession') and sse[-2]['turnover']>0 else None
 return {'turnoverSseSzse':turnover,'shanghaiVolumeChange':volume_change,'asOf':d.get('targetSession'),'retrievedAt':d.get('retrievedAt'),'title':title,'indexSample':len(indices),'negativeIndices':negative,'windows':{str(n):{'start':days[-n-1] if len(days)>n else None,'end':days[-1] if days else None} for n in (5,20,60)},'windowStart':days[-21] if len(days)>20 else None,'windowEnd':days[-1] if days else None,'rows':rows,'pairs':pairs,'limits':'selected instruments; matched endpoint price/NAV changes, not total return; correlations are historical, not tail hedge certificates'}
