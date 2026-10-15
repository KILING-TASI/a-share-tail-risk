import unittest,sys,json,copy,subprocess,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skill/scripts'))
from risk_lab import evaluate
from build_observations import derive
from research_extensions import extend

class Lab(unittest.TestCase):
 def setUp(self):self.fs=json.loads((ROOT/'tests/lab-fixtures.json').read_text(encoding='utf-8'))
 def test_late_receipt_does_not_hide_failure(self):self.assertEqual(evaluate(self.fs[3])['firstShortfallMonth'],6)
 def test_immediate_sale(self):d=self.fs[3];d['exitDelayMonths']=0;self.assertEqual(evaluate(d)['rows'][0]['endCash'],60000)
 def test_after_horizon_no_proceeds(self):d=self.fs[3];d['exitDelayMonths']=24;self.assertEqual(evaluate(d)['rows'][-1]['endCash'],-70000)
 def test_no_income_shock(self):d=self.fs[3];d['incomeLossPct']=0;d['stressedSaleProceeds']=0;self.assertIsNone(evaluate(d)['firstShortfallMonth'])
 def test_fractional_month_rejected(self):d=self.fs[3];d['months']=1.5;self.assertRaises(ValueError,evaluate,d)
 def test_income_shock_bounds(self):d=self.fs[3];d['incomeLossPct']=101;self.assertRaises(ValueError,evaluate,d)
 def test_unverified_loss_not_budget_certified(self):self.assertIsNone(evaluate(self.fs[1])['budgetHeadroom'])
 def test_reserve_stress(self):self.assertEqual(evaluate(self.fs[1])['reserveHeadroom'],-5000)
 def test_verified_loss_includes_cost(self):d=self.fs[1];d['lossBoundVerified']=True;self.assertEqual(evaluate(d)['budgetHeadroom'],-500)
 def test_blocked_cannot_exceed_reserve(self):d=self.fs[1];d['blockedSafe']=100001;self.assertRaises(ValueError,evaluate,d)
 def test_costs_and_opportunity(self):self.assertEqual(evaluate(self.fs[2])['totalCost'],5200)
 def test_zero_payout_still_loses_premium(self):self.assertEqual(evaluate(self.fs[2])['rows'][0]['netProtection'],-5200)
 def test_not_double_count_loss(self):self.assertEqual(evaluate(self.fs[2])['rows'][1]['combinedPnL'],-21200)
 def test_fractional_renewals_rejected(self):d=self.fs[2];d['terms']=1.1;self.assertRaises(ValueError,evaluate,d)
 def test_collateral_call_not_price_loss(self):r=evaluate(self.fs[0])['rows'][-1];self.assertEqual(r['priceLoss'],150000);self.assertEqual(r['cashCall'],65000)
 def test_unknown_maintenance_unknown_cash(self):d=self.fs[0];d['maintenanceRatio']=None;self.assertIsNone(evaluate(d)['rows'][0]['cashHeadroom'])
 def test_unlevered_call_zero(self):d=self.fs[0];d['debt']=0;d['maintenanceRatio']=None;self.assertEqual(evaluate(d)['rows'][0]['cashCall'],0)
 def test_sorted_shocks_required(self):d=self.fs[0];d['shocksPct']=[0,30,10];self.assertRaises(ValueError,evaluate,d)
 def test_bool_rejected(self):d=self.fs[0];d['cash']=True;self.assertRaises(ValueError,evaluate,d)
 def test_infinite_rejected(self):d=self.fs[0];d['cash']=float('inf');self.assertRaises(ValueError,evaluate,d)
 def test_browser_python_parity(self):
  code="const fs=require('fs'),lab=require('./skill/assets/risk-lab.js');console.log(JSON.stringify(JSON.parse(fs.readFileSync('tests/lab-fixtures.json')).map(lab.evaluate)))"
  out=json.loads(subprocess.check_output(['node','-e',code],cwd=ROOT,text=True,encoding='utf-8'))
  for inp,actual in zip(self.fs,out):
   expected=evaluate(inp)
   for k,v in actual.items():self.assertEqual(expected[k],v)

class BreadthDepth(unittest.TestCase):
 def setUp(self):
  days=[str(datetime.date(2026,1,1)+datetime.timedelta(days=i)) for i in range(65)]
  self.meta={'expectedSessions':days,'poolCodes':['a','b'],'poolId':'fixed-synthetic','ruleVersion':'synthetic','methodVerified':True,'groups':{'a':{'exchange':'SSE','size':'large'},'b':{'exchange':'BSE','size':'small'}}}
  self.rows=[{'date':day,'code':code,'close':str(100+i if code=='a' else 100),'prevClose':str(99+i if code=='a' else 100),'volume':'100','status':'trading','limitDown':'0','turnover':str(10 if i==64 else 100)} for i,day in enumerate(days) for code in ['a','b']]
 def test_median_and_denominator(self):r=derive(self.rows,self.meta)['breadth'];self.assertEqual(r['tradingCount'],2);self.assertEqual(r['upRatioTrading'],.5)
 def test_ma60_eligible(self):r=derive(self.rows,self.meta)['breadth'];self.assertEqual(r['ma60Eligible'],2);self.assertEqual(r['ma60Ratio'],.5)
 def test_new_high_excludes_today(self):r=derive(self.rows,self.meta)['breadth'];self.assertEqual(r['newHigh20Ratio'],.5)
 def test_group_denominator(self):r=derive(self.rows,self.meta)['breadth']['groups']['exchange'];self.assertEqual(r['BSE']['tradingCount'],1);self.assertEqual(r['SSE']['upRatioTrading'],1)
 def test_missing_turnover_unknown(self):
  for r in self.rows:r.pop('turnover')
  self.assertIsNone(derive(self.rows,self.meta)['exitPressure']['turnoverContracted'])
 def test_contraction_prior20(self):self.assertEqual(derive(self.rows,self.meta)['exitPressure']['turnoverContracted'],2)
 def test_short_window_not_zero(self):self.meta['expectedSessions']=self.meta['expectedSessions'][:1];self.assertIsNone(derive(self.rows[:2],self.meta)['breadth']['ma60Ratio'])
 def test_suspend_excluded_trading(self):self.rows[-1].update(status='suspended',volume='0');self.assertEqual(derive(self.rows,self.meta)['breadth']['tradingCount'],1)
 def test_suspended_volume_inconsistent(self):self.rows[-1]['status']='suspended';self.assertRaises(ValueError,derive,self.rows,self.meta)

class Extensions(unittest.TestCase):
 def setUp(self):
  self.d={'targetSession':'2026-10-14','records':[{'id':'a','date':'2026-10-13','status':'available','history':[{'date':'2026-10-12','value':100},{'date':'2026-10-13','value':80}]}]}
 def test_original_normalised_no_raw(self):r=extend(self.d,{})['trends'][0]['points'];self.assertEqual(r[1]['relative'],80);self.assertNotIn('value',r[0])
 def test_drawdown(self):self.assertAlmostEqual(extend(self.d,{})['trends'][0]['points'][1]['drawdown'],-.2)
 def test_stale_not_fresh(self):self.assertEqual(extend(self.d,{})['coverageMatrix'][0]['calendarLagDays'],1)
 def test_missing_breadth_empty(self):self.assertEqual(extend(self.d,{})['breadthHistory'],[])
 def test_unknown_previous(self):self.assertFalse(extend(self.d,{})['previousAvailable'])
 def test_same_day_not_progress(self):self.assertRaises(ValueError,extend,self.d,{},dict(asOf='2026-10-14'))
 def test_previous_date_advancement(self):p={'asOf':'2026-10-12','rows':[{'id':'a','date':'2026-10-12'}]};self.assertEqual(len(extend(self.d,{},p)['changes']),1)
 def test_duplicate_history_rejected(self):self.d['records'][0]['history']*=2;self.assertRaises(ValueError,extend,self.d,{})
 def test_rate_not_price_chart(self):self.d['records'][0]['kind']='rate';self.assertEqual(extend(self.d,{})['trends'],[])
 def test_future_filtered(self):self.d['records'][0]['history'].append({'date':'2026-10-15','value':60});self.assertEqual(len(extend(self.d,{})['trends'][0]['points']),2)
