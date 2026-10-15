# SPDX-License-Identifier: MIT
"""Shared WDI response parser. Decimal text, nulls, identity and pagination checks."""
import json,re
from decimal import Decimal

def unique(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise ValueError('duplicate JSON key')
  d[k]=v
 return d
def bad(v):raise ValueError('non-finite JSON number')
def parse(raw,spec,page=1):
 obj=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique,parse_float=str,parse_constant=bad)
 if not isinstance(obj,list) or len(obj)!=2 or not isinstance(obj[0],dict) or not isinstance(obj[1],list):raise ValueError('not WDI observation pages')
 meta,data=obj;pages=int(meta['pages']);total=int(meta['total'])
 if int(meta['page'])!=page or not 1<=pages<=10 or not 0<=total<=50000:raise ValueError('invalid WDI pagination')
 records=[];seen=set()
 for row in data:
  code=row['countryiso3code'];period=row['date'];indicator=row['indicator'];key=(code,indicator['id'],period)
  if code not in spec['countries'] or indicator['id']!=spec['indicator'] or not re.fullmatch('[0-9]{4}',period) or not spec['start']<=int(period)<=spec['end'] or key in seen:raise ValueError('WDI identity, period or duplicate mismatch')
  seen.add(key);value=row['value']
  if value is not None:
   if isinstance(value,bool):raise ValueError('boolean observation')
   value=Decimal(str(value))
   if not value.is_finite():raise ValueError('non-finite observation')
  records.append(dict(indicatorId=indicator['id'],indicatorName=indicator['value'],regionCode=code,regionName=row.get('country',{}).get('value'),period=period,value=None if value is None else str(value),unit=row.get('unit') or None,unknownReason='来源值为空' if value is None else None,footnote=row.get('footnote'),regionClassification='not-verified'))
 return meta,records
