import unittest,sys,copy,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skill/scripts'))
import risk_math as r
class RiskMath(unittest.TestCase):
 def p(self):return dict(unleveredLinear=True,cashWeight=.8,cashShock=0,positions=[dict(id='synthetic',weight=.2,shock=-1)])
 def test_recovery_50(self):self.assertEqual(r.recovery(dict(drawdown=.5))['requiredGain'],1)
 def test_total_loss_no_infinite_gain(self):self.assertIsNone(r.recovery(dict(drawdown=1))['requiredGain'])
 def test_no_loss(self):self.assertEqual(r.recovery(dict(drawdown=0))['requiredGain'],0)
 def test_compounding(self):self.assertAlmostEqual(r.limit_path(dict(dailyDrop=.1,days=3))['compoundedLoss'],.271)
 def test_compounding_not_execution(self):self.assertFalse(r.limit_path(dict(dailyDrop=.1,days=3))['executionGuaranteed'])
 def test_wrong_day_types(self):
  for n in [True,0,1.5,1001]:
   with self.assertRaises(ValueError):r.limit_path(dict(dailyDrop=.1,days=n))
 def test_declared_portfolio(self):
  v=r.portfolio(self.p());self.assertAlmostEqual(v['declaredReturn'],-.2);self.assertEqual(v['recovery']['requiredGain'],.25);self.assertFalse(v['liquidationCashCertified'])
 def test_no_implicit_cash(self):
  p=self.p();p['cashWeight']=.7
  with self.assertRaises(ValueError):r.portfolio(p)
 def test_no_implicit_leverage(self):
  p=self.p();p['unleveredLinear']=False
  with self.assertRaises(ValueError):r.portfolio(p)
 def test_missing_cash_risk(self):
  p=self.p();p.pop('cashShock')
  with self.assertRaises(KeyError):r.portfolio(p)
 def test_duplicate(self):
  p=self.p();p['positions'].append(p['positions'][0])
  with self.assertRaises(ValueError):r.portfolio(p)
 def test_unknown_position_shock(self):
  p=self.p();p['positions'][0]['shock']=None
  with self.assertRaises(ValueError):r.portfolio(p)
 def test_nonfinite_and_bool(self):
  for v in [float('nan'),float('inf'),True,'0.2']:
   with self.assertRaises(ValueError):r.recovery(dict(drawdown=v))
 def test_declared_cash_loss(self):
  p=self.p();p['cashShock']=-.1;self.assertAlmostEqual(r.portfolio(p)['declaredReturn'],-.28)
 def test_all_cash(self):self.assertEqual(r.portfolio(dict(unleveredLinear=True,cashWeight=1,cashShock=0,positions=[]))['relativeEndingValue'],1)
 def test_no_probability(self):
  p=r.review(dict(basis='synthetic',portfolio=self.p()));self.assertFalse(p['sourceVerified']);self.assertFalse(p['probabilityEstimated'])
 def test_requires_basis(self):
  with self.assertRaises(ValueError):r.review(dict(recovery=dict(drawdown=.2)))
 def test_positive_scenario_no_recovery_needed(self):
  p=self.p();p['positions'][0]['shock']=1;self.assertEqual(r.portfolio(p)['recovery']['requiredGain'],0)
if __name__=='__main__':unittest.main()
