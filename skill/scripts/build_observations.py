"""Derive breadth/exit proxies from an authorised dated CSV and verified pool metadata."""
import argparse,csv,json,math,statistics
from collections import defaultdict
from datetime import date
from pathlib import Path
from market_gates import session_date

def derive(rows,meta):
 sessions=meta['expectedSessions'];pool=meta['poolCodes']
 if len(set(pool))!=len(pool) or not pool:raise ValueError('pool empty or duplicate')
 if not sessions or sorted(set(sessions))!=sessions:raise ValueError('calendar unordered or duplicate')
 for day in sessions:session_date(day)
 tolerance=meta.get('priceTolerance',0)
 if isinstance(tolerance,bool) or not isinstance(tolerance,(int,float)) or not math.isfinite(tolerance) or tolerance<0:raise ValueError('invalid price tolerance')
 if not meta.get('poolId') or not meta.get('ruleVersion') or meta.get('methodVerified') is not True:raise ValueError('pool and method verification required')
 grouped=defaultdict(dict)
 for r in rows:
  if r['date'] not in sessions or r['code'] not in pool:raise ValueError('date or security outside declared pool')
  if r['code'] in grouped[r['date']]:raise ValueError('duplicate daily security')
  grouped[r['date']][r['code']]=r
 history=[];exitrows=[];paths={c:[] for c in pool};turnovers={c:[] for c in pool};groups=meta.get('groups',{})
 for c,g in groups.items():
  if c not in pool or not isinstance(g,dict):raise ValueError('invalid group metadata')
 def numeric(v):
  x=float(v)
  if not math.isfinite(x) or x<0:raise ValueError('invalid nonnegative observation')
  return x
 for day in sessions:
  dayrows=grouped[day]
  if set(dayrows)!=set(pool):raise ValueError('incomplete daily stock pool: '+day)
  up=down=flat=suspended=zero=limits=0;limits_known=True;stats=[];contracted=0;turnover_known=0
  for r in dayrows.values():
   close=numeric(r['close']);previous=numeric(r['prevClose']);volume=numeric(r['volume'])
   if close<=0 or previous<=0:raise ValueError('price/reference close missing')
   if r['status'] not in ('trading','suspended'):raise ValueError('unknown trading status')
   up+=close>previous;down+=close<previous;flat+=close==previous;suspended+=r['status']=='suspended';zero+=close<previous and volume==0
   if r['status']=='suspended' and (volume!=0 or close!=previous):raise ValueError('suspended security has volume')
   ret=close/previous-1
   chain=paths[r['code']];chain.append((chain[-1] if chain else 1)*(1+ret))
   if not math.isfinite(chain[-1]) or chain[-1]<=0:raise ValueError('adjusted path overflow')
   tr=turnovers[r['code']];tv=None if r.get('turnover','')=='' else numeric(r['turnover']);baseline=tr[-20:];tr.append(tv)
   if tv is not None and len(baseline)==20 and all(x is not None for x in baseline) and statistics.mean(baseline)>0:
    turnover_known+=1;contracted+=tv<statistics.mean(baseline)*.5
   stats.append(dict(code=r['code'],trading=r['status']=='trading',ret=ret,ma20=chain[-1]>statistics.mean(chain[-20:]) if len(chain)>=20 else None,ma60=chain[-1]>statistics.mean(chain[-60:]) if len(chain)>=60 else None,newHigh20=chain[-1]>max(chain[-21:-1]) if len(chain)>=21 else None,newLow20=chain[-1]<min(chain[-21:-1]) if len(chain)>=21 else None))
   limit=r.get('limitDown','')
   if limit=='':limits_known=False
   else:
    lv=numeric(limit)
    if lv>0:limits+=r['status']=='trading' and close<=lv+tolerance
  def aggregate(items):
   traded=[x for x in items if x['trading']]
   result={'tradingCount':len(traded),'upRatioTrading':sum(x['ret']>0 for x in traded)/len(traded) if traded else None,'medianChange':statistics.median(x['ret'] for x in traded) if traded else None}
   for k in ('ma20','ma60','newHigh20','newLow20'):
    known=[x[k] for x in traded if x[k] is not None];result[k+'Eligible']=len(known);result[k+'Ratio']=sum(known)/len(known) if known else None
   return result
  grouped_stats={}
  for axis in ('exchange','size'):
   labels=sorted({g[axis] for g in groups.values() if axis in g})
   grouped_stats[axis]={label:aggregate([x for x in stats if groups.get(x['code'],{}).get(axis)==label]) for label in labels}
  history.append(dict(**aggregate(stats),groups=grouped_stats,date=day,up=up,down=down,flat=flat,total=len(pool),poolId=meta['poolId'],methodVerified=True))
  exitrows.append(dict(date=day,poolId=meta['poolId'],ruleVersion=meta['ruleVersion'],methodVerified=True,expected=len(pool),reported=len(pool),downLimit=limits if limits_known else None,suspended=suspended,zeroVolumeDown=zero,turnoverContracted=contracted if turnover_known else None,turnoverEligible=turnover_known))
 return {'asOf':sessions[-1],'expectedSessions':sessions,'breadthHistory':history,'breadth':history[-1],'exitPressure':exitrows[-1],'exitHistory':exitrows,'groupBasis':meta.get('groupBasis','declared static cohorts; not point-in-time historical membership'),'breadthScope':meta.get('scope','selected'),'exitScope':meta.get('scope','selected'),'limits':'declared pool and rule inputs; not true execution inability; suspensions included in breadth denominator as observed reference-close comparison'}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--csv',required=True);ap.add_argument('--metadata',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();out=Path(a.output)
 with Path(a.csv).open(encoding='utf-8-sig',newline='') as f:result=derive(list(csv.DictReader(f)),json.loads(Path(a.metadata).read_text(encoding='utf-8')))
 out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,allow_nan=False,indent=2)
if __name__=='__main__':main()
