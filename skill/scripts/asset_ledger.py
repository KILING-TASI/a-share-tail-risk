"""Declared multi-asset stress ledger. No market forecasting or execution."""
import argparse,json,math,sys
from datetime import date
from pathlib import Path

def number(v):
 if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise ValueError('amount must be a finite nonnegative number')
 return v

def analyze(d):
 date.fromisoformat(d['asOf']);currency=d['reportingCurrency']
 if not isinstance(currency,str) or not currency:raise ValueError('reporting currency absent')
 rows=d['assets'];ids=[r['id'] for r in rows]
 if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):raise ValueError('asset identities must be unique')
 known=0;unknown=[]
 for r in rows:
  if r.get('reportingValue') is None:unknown.append(r['id'])
  else:known+=number(r['reportingValue'])
 debt=0;unknown_debt=[];liability_ids=[r['id'] for r in d.get('liabilities',[])]
 if any(not isinstance(i,str) or not i for i in liability_ids) or len(set(liability_ids))!=len(liability_ids):raise ValueError('liability identities must be unique')
 for r in d.get('liabilities',[]):
  if r.get('reportingValue') is None:unknown_debt.append(r['id'])
  else:debt+=number(r['reportingValue'])
 scenarios=[]
 for s in d.get('scenarios',[]):
  total=0;missing=[];values=[]
  for r in rows:
   shock=s.get('shocksPct',{}).get(r['id']);v=r.get('reportingValue')
   if v is None or shock is None:missing.append(r['id']);continue
   if isinstance(shock,bool) or not isinstance(shock,(int,float)) or not math.isfinite(shock) or shock< -100:raise ValueError('shock must be finite and no lower than -100 percent')
   result=v*(1+shock/100)
   if not math.isfinite(result):raise ValueError('scenario amount overflow')
   total+=result;values.append({'id':r['id'],'scenarioValue':result})
  if not math.isfinite(total):raise ValueError('scenario total overflow')
  scenarios.append({'name':s['name'],'coveredScenarioAssetValue':total,'missingAssets':missing,'completeDeclaredAssetScenario':not missing,'positions':values,'limits':'asset value only; debts, FX and cash availability are not automatically stressed'})
 cash=d.get('availableCash');need=d.get('requiredOutflow');headroom=None if cash is None or need is None else number(cash)-number(need)
 if not all(math.isfinite(x) for x in [known,debt]):raise ValueError('ledger total overflow')
 return {'asOf':d['asOf'],'reportingCurrency':currency,'knownAssetValue':known,'unknownAssets':unknown,'knownLiabilityValue':debt,'unknownLiabilities':unknown_debt,'knownAssetsLessKnownLiabilities':known-debt,'inventoryCompleteDeclared':d.get('inventoryComplete') is True,'fullNetWorthCertified':False,'cashHeadroom':headroom,'cashStatus':'unknown' if headroom is None else ('shortfall' if headroom<0 else 'covers-declared-outflow'),'scenarios':scenarios,'limits':'declared records only; not full wealth, liquidity, probability or safety certification'}

def main():
 if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
 ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);a=ap.parse_args()
 try:print(json.dumps(analyze(json.loads(Path(a.input).read_text(encoding='utf-8'))),ensure_ascii=False,allow_nan=False,indent=2))
 except (KeyError,TypeError,ValueError,OSError) as e:ap.exit(2,'无法完成清单核验：'+str(e)+'\n')
if __name__=='__main__':main()
