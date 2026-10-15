"""Strict observation matching. No fuzzy identities, implicit FX or invented vintages."""
import argparse,calendar,json,math,re
from datetime import date,datetime,timezone,timedelta
from pathlib import Path

def validate(r):
 for k in ('entityId','metric','region','frequency','period','unit','basis','sourceUrl'):
  if not isinstance(r.get(k),str) or not r[k]:raise ValueError('missing '+k)
 if not r['sourceUrl'].startswith('https://'):raise ValueError('HTTPS source required')
 x=r.get('value')
 if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):raise ValueError('finite numeric observation required')
 f=r['frequency'];p=r['period']
 if f=='annual':
  if not re.fullmatch(r'\d{4}',p):raise ValueError('annual period must be YYYY')
  date(int(p),12,31)
 elif f=='monthly':
  if not re.fullmatch(r'\d{4}-\d{2}',p):raise ValueError('monthly period must be YYYY-MM')
  date.fromisoformat(p+'-01')
 elif f=='daily':
  if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',p):raise ValueError('daily period must be YYYY-MM-DD')
  date.fromisoformat(p)
 else:raise ValueError('unsupported frequency')
 if r.get('availableAt') is not None:
  if datetime.fromisoformat(r['availableAt'].replace('Z','+00:00')).tzinfo is None:raise ValueError('release timestamp timezone required')
 return r

def deduplicate(records):
 out={};conflicts=[]
 for r in records:
  validate(r);key=tuple(r.get(k) for k in ('entityId','metric','period','frequency','unit','currency','basis','shareClass','version'))
  if key in out and out[key] is not None and out[key]['value']!=r['value']:conflicts.append({'key':list(key),'reason':'conflicting values; neither automatically preferred'});out[key]=None
  elif key not in out:out[key]=r
 return {'records':[v for v in out.values() if v is not None],'conflicts':conflicts}

def match_window(reference,candidate,n):
 """Exact benchmark endpoints, no nearest-day substitute or forward filling."""
 if len(reference)<=n:return {'status':'rejected','reason':'benchmark history too short','change':None}
 days=[x['date'] for x in reference]
 values={x['date']:x['value'] for x in candidate}
 if len(values)!=len(candidate) or days!=sorted(set(days)) or [x['date'] for x in candidate]!=sorted(values):raise ValueError('duplicate or unordered window data')
 start,end=days[-n-1],days[-1]
 if start not in values or end not in values:return {'status':'rejected','reason':'exact start/end missing','start':start,'end':end,'change':None}
 for x in (values[start],values[end]):
  if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0:raise ValueError('nonpositive endpoint')
 return {'status':'conditional-match','reason':'exact dates; own-currency price/NAV change, not total return','start':start,'end':end,'change':values[end]/values[start]-1}

def match(left,right,mode='same-series',cutoff=None,point_in_time=False):
 validate(left);validate(right);reasons=[]
 keys=['frequency','period','unit','currency','basis']
 if mode=='same-series':keys+=['entityId','metric','shareClass','region']
 elif mode=='cross-region':keys+=['metric']
 elif mode=='premium':
  keys+=['entityId','shareClass','region']
  if left['metric']!='market_price' or right['metric']!='published_unit_nav':reasons.append('requires market_price and published_unit_nav; estimates refused')
  if left['value']<=0 or right['value']<=0:reasons.append('price and NAV must be positive')
 else:raise ValueError('unsupported match mode')
 for k in keys:
  if left.get(k)!=right.get(k):reasons.append(k+' mismatch')
 if mode=='premium' and (not left.get('currency') or not left.get('shareClass')):reasons.append('currency and share class must be explicit')
 if cutoff:
  date.fromisoformat(cutoff)
  for label,r in [('left',left),('right',right)]:
   period_end=r['period']+('-12-31' if r['frequency']=='annual' else '-'+str(calendar.monthrange(int(r['period'][:4]),int(r['period'][5:]))[1]) if r['frequency']=='monthly' else '')
   if period_end>cutoff:reasons.append(label+' observation after cutoff')
 if point_in_time:
  if not cutoff:raise ValueError('point-in-time cutoff required')
  for label,r in [('left',left),('right',right)]:
   if not r.get('availableAt'):reasons.append(label+' release timestamp unknown; no historical availability claim')
   elif datetime.fromisoformat(r['availableAt'].replace('Z','+00:00'))>=datetime.combine(date.fromisoformat(cutoff)+timedelta(days=1),datetime.min.time(),timezone(timedelta(hours=8))):reasons.append(label+' released after cutoff (Asia/Shanghai day end)')
 return {'status':'rejected' if reasons else 'conditional-match','reasons':reasons,'mode':mode,'premium':left['value']/right['value']-1 if mode=='premium' and not reasons else None,'limits':'declared identifiers and units; source metadata not authenticated; same-day price/NAV need not be contemporaneous or executable; no interpolation or automatic FX'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);a=p.parse_args()
 try:
  d=json.loads(Path(a.input).read_text(encoding='utf-8'))
  print(json.dumps(match(d['left'],d['right'],d.get('mode','same-series'),d.get('cutoff'),d.get('pointInTime',False)),ensure_ascii=False,allow_nan=False,indent=2))
 except (KeyError,TypeError,ValueError,OSError) as e:p.exit(2,'无法匹配，请核对标识与口径：'+str(e)+'\n')
if __name__=='__main__':main()
