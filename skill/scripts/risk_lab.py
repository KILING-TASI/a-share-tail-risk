"""Explicit deterministic stress tools; no probabilities or trading advice."""
import argparse,json,math
from pathlib import Path

def num(x,lo=0):
 if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<lo:raise ValueError('finite number outside allowed range')
 return x

def evaluate(d):
 mode=d['tool']
 if mode=='fragility':
  equity=num(d['equity']);debt=num(d['debt']);cash=num(d['cash']);need=num(d['cashNeed']);floor=num(d['equityFloor']);haircut=num(d['haircutPct'])/100
  if haircut>1:raise ValueError('haircut above 100%')
  maintenance=d.get('maintenanceRatio');maintenance=None if maintenance is None else num(maintenance,1)
  shocks=d['shocksPct']
  if len(shocks)<3 or len(set(shocks))!=len(shocks) or sorted(shocks)!=shocks:raise ValueError('three or more unique ascending shocks required')
  rows=[]
  for s in shocks:
   x=num(s)
   if x>100:raise ValueError('shock above 100%')
   collateral=(equity+debt)*(1-x/100)*(1-haircut);call=max(0,maintenance*debt-collateral) if maintenance is not None and debt else (0 if debt==0 else None)
   headroom=None if call is None else cash-need-call
   rows.append({'shockPct':x,'equityAfter':(equity+debt)*(1-x/100)-debt,'priceLoss':(equity+debt)*x/100,'collateralAfter':collateral,'cashCall':call,'cashHeadroom':headroom,'floorBreached':(equity+debt)*(1-x/100)-debt<floor})
  return {'tool':mode,'rows':rows,'firstCashBreachPct':next((r['shockPct'] for r in rows if r['cashHeadroom'] is not None and r['cashHeadroom']<0),None),'limits':'linear prices; collateral top-up is cash locked, not additional price loss; no broker liquidation path; missing maintenance means unknown call'}
 if mode=='barbell':
  safe=num(d['safeAmount']);haircut=num(d['safeHaircutPct'])/100;blocked=num(d['blockedSafe']);need=num(d['requiredReserve']);risky=num(d['riskAmount']);loss=num(d['maxLossPct'])/100;budget=num(d['lossBudget']);cost=num(d['cost']);verified=d.get('lossBoundVerified') is True
  if haircut>1 or loss>1 or blocked>safe:raise ValueError('invalid fraction or blocked reserve')
  reserve=max(0,safe*(1-haircut)-blocked);worst=risky*loss+cost
  return {'tool':mode,'usableReserve':reserve,'reserveHeadroom':reserve-need,'declaredRiskLoss':worst,'budgetHeadroom':budget-worst if verified else None,'lossBoundVerified':verified,'commonRiskReviewed':d.get('commonRiskReviewed') is True,'limits':'declared stressed reserve and contractual loss bound; unknown common risks or loss bounds cannot certify barbell safety; no recommended allocation'}
 if mode=='protection':
  premium=num(d['premiumPerTerm']);terms=num(d['terms'],1)
  if terms!=int(terms):raise ValueError('terms must be integer')
  cost=premium*terms+num(d['fees'])+num(d['cashReserve'])*num(d['opportunityRatePct'])/100*num(d['months'])/12;budget=num(d['budget']);rows=[]
  for r in d['scenarios']:
   payout=num(r['grossPayout']);basis=num(r.get('basisSlippage',0));loss=num(r['underlyingLoss']);net=payout-basis-cost
   rows.append({'label':r['label'],'netProtection':net,'combinedPnL':net-loss})
  return {'tool':mode,'totalCost':cost,'budgetHeadroom':budget-cost,'rows':rows,'limits':'fixed assumed renewal premium and simple annual opportunity cost, no double-counted principal; payout supplied by user, not option pricing or probability; seller obligations excluded'}
 if mode=='cashflow':
  months=d['months'];cash=num(d['cash']);income=num(d['monthlyIncome']);income_loss=num(d['incomeLossPct'])/100;expense=num(d['monthlyExpense']);debt=num(d['monthlyDebt']);delay=d['exitDelayMonths'];proceeds=num(d['stressedSaleProceeds']);rows=[]
  if not isinstance(months,int) or isinstance(months,bool) or not 1<=months<=120 or not isinstance(delay,int) or isinstance(delay,bool) or not 0<=delay<=120 or income_loss>1:raise ValueError('invalid month or fraction')
  if delay==0:cash+=proceeds
  for m in range(1,months+1):
   cash+=income*(1-income_loss)-expense-debt
   if m==delay:cash+=proceeds
   if not math.isfinite(cash):raise ValueError('overflow')
   rows.append({'month':m,'endCash':cash})
  return {'tool':mode,'rows':rows,'firstShortfallMonth':next((r['month'] for r in rows if r['endCash']<0),None),'limits':'month-end model; intramonth shortfalls not covered; sale proceeds are stressed net available amount, not current market value; expenses exclude separately entered debt service'}
 raise ValueError('unknown tool')

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);a=p.parse_args()
 try:
  result=evaluate(json.loads(Path(a.input).read_text(encoding='utf-8')))
  print(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2))
 except (KeyError,TypeError,ValueError,OSError) as e:p.exit(2,'无法计算，请核对输入：'+str(e)+'\n')
if __name__=='__main__':main()
