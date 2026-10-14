import unittest,sys,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skill/scripts'))
import asset_ledger as a
class Ledger(unittest.TestCase):
 def setUp(self):self.d=json.loads((ROOT/'skill/examples/asset-ledger.json').read_text(encoding='utf-8'))
 def run_ledger(self):return a.analyze(self.d)
 def test_unknown_not_full(self):r=self.run_ledger();self.assertEqual(r['unknownAssets'],['property']);self.assertFalse(r['fullNetWorthCertified'])
 def test_cash_shortfall(self):self.assertEqual(self.run_ledger()['cashHeadroom'],-30000)
 def test_unknown_cash(self):self.d['availableCash']=None;self.assertIsNone(self.run_ledger()['cashHeadroom'])
 def test_zero_cash(self):self.d['availableCash']=0;self.assertEqual(self.run_ledger()['cashHeadroom'],-80000)
 def test_known_partial_stress(self):r=self.run_ledger()['scenarios'][0];self.assertEqual(r['coveredScenarioAssetValue'],215000);self.assertFalse(r['completeDeclaredAssetScenario'])
 def test_missing_shock(self):del self.d['scenarios'][0]['shocksPct']['equity'];self.assertIn('equity',self.run_ledger()['scenarios'][0]['missingAssets'])
 def test_duplicate(self):
  self.d['assets'][1]['id']='cash'
  with self.assertRaises(ValueError):self.run_ledger()
 def test_bool_amount(self):
  self.d['assets'][0]['reportingValue']=True
  with self.assertRaises(ValueError):self.run_ledger()
 def test_total_loss(self):self.d['scenarios'][0]['shocksPct']['equity']=-100;self.assertEqual(self.run_ledger()['scenarios'][0]['positions'][-1]['scenarioValue'],0)
 def test_excess_loss(self):
  self.d['scenarios'][0]['shocksPct']['equity']=-101
  with self.assertRaises(ValueError):self.run_ledger()
 def test_claim_complete_not_certified(self):self.d['inventoryComplete']=True;self.assertFalse(self.run_ledger()['fullNetWorthCertified'])
 def test_no_auto_debt_stress(self):self.d['liabilities'][0]['reportingValue']=200000;self.assertEqual(self.run_ledger()['knownLiabilityValue'],200000)

 def test_duplicate_liability(self):
  self.d['liabilities']*=2
  with self.assertRaises(ValueError):self.run_ledger()
 def test_overflow_scenario(self):
  self.d['assets']=[{'id':'a','reportingValue':1e308},{'id':'b','reportingValue':1e307}];self.d['scenarios']=[{'name':'overflow','shocksPct':{'a':70,'b':100}}]
  with self.assertRaises(ValueError):self.run_ledger()
