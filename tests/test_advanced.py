import unittest,sys,copy,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skill/scripts'))
import risk_math as r
class Advanced(unittest.TestCase):
 def fixture(self):return json.loads((Path(__file__).resolve().parents[1]/'skill/examples/advanced-scenarios.json').read_text(encoding='utf-8'))
 def test_arithmetic_not_compound(self):
  v=r.compound_path({'returns':[.5,-.5]});self.assertEqual(v['arithmeticMean'],0);self.assertEqual(v['endingRelativeValue'],.75);self.assertAlmostEqual(v['maxDrawdownInDeclaredPath'],.5)
 def test_total_loss_absorbs(self):self.assertEqual(r.compound_path({'returns':[-1,100]})['relativePath'],[0,0])
 def test_geometric_product(self):
  v=r.compound_path({'returns':[.1,.2]});self.assertAlmostEqual((1+v['geometricMean'])**2,1.32)
 def test_underflow_not_ruin(self):
  with self.assertRaises(ValueError):r.compound_path({'returns':[-.99]*1000})
 def test_overflow(self):
  with self.assertRaises(ValueError):r.compound_path({'returns':[1e308,1e308]})
 def test_bad_returns(self):
  for v in [[],[-1.01],[True],[None]]:
   with self.assertRaises(ValueError):r.compound_path({'returns':v})
 def test_cash_gap(self):
  v=r.cash_constraints(self.fixture()['cashConstraints'])['snapshots'][0];self.assertEqual(v['cashHeadroom'],-10);self.assertEqual(v['collateralStatus'],'below-declared-ratio')
 def test_unknown_not_pass(self):
  v=r.cash_constraints(self.fixture()['cashConstraints'])['snapshots'][1];self.assertEqual(v['cashStatus'],'unknown');self.assertEqual(v['collateralStatus'],'unknown')
 def test_zero_cash_is_not_unknown(self):
  p=self.fixture()['cashConstraints'];p['snapshots'][0]['availableCash']=0;self.assertEqual(r.cash_constraints(p)['snapshots'][0]['cashHeadroom'],-110)
 def test_no_debt_not_fake_ratio(self):
  p=self.fixture()['cashConstraints'];p['snapshots'][0]['debt']=0;v=r.cash_constraints(p)['snapshots'][0];self.assertIsNone(v['declaredCollateralRatio']);self.assertEqual(v['collateralStatus'],'no-declared-debt')
 def test_snapshot_no_guarantee(self):
  p=self.fixture()['cashConstraints'];p['snapshots'][0]['availableCash']=200;v=r.cash_constraints(p);self.assertFalse(v['survivalCertified']);self.assertFalse(v['contractVerified'])
 def test_unknown_contract_threshold(self):
  p=self.fixture()['cashConstraints'];p['snapshots'][0]['requiredRatio']=None;self.assertEqual(r.cash_constraints(p)['snapshots'][0]['collateralStatus'],'unknown')
 def test_invalid_partially_unknown_cash(self):
  p=self.fixture()['cashConstraints'];p['snapshots'][1]['dueCash']=-1
  with self.assertRaises(ValueError):r.cash_constraints(p)
 def test_wrong_snapshot_basis(self):
  p=self.fixture()['cashConstraints'];p['snapshotValuesAfterPriorPayments']=False
  with self.assertRaises(ValueError):r.cash_constraints(p)
 def test_wrong_currency(self):
  p=self.fixture()['cashConstraints'];p['unit']='USD'
  with self.assertRaises(ValueError):r.cash_constraints(p)
 def test_duplicate_dates(self):
  p=self.fixture()['cashConstraints'];p['snapshots'][1]['date']=p['snapshots'][0]['date']
  with self.assertRaises(ValueError):r.cash_constraints(p)
 def test_joint_not_summed(self):
  v=r.joint_shocks(self.fixture()['jointShocks']);self.assertEqual(v['worstDeclaredReturn'],-.24);self.assertEqual(len(v['scenarios']),2);self.assertFalse(v['probabilityEstimated'])
 def test_missing_joint_position(self):
  p=self.fixture()['jointShocks'];p['scenarios'][0]['shocks'].pop('B')
  with self.assertRaises(ValueError):r.joint_shocks(p)
 def test_unknown_joint_shock(self):
  p=self.fixture()['jointShocks'];p['scenarios'][0]['shocks']['B']=None
  with self.assertRaises(ValueError):r.joint_shocks(p)
 def test_duplicate_joint_scenarios(self):
  p=self.fixture()['jointShocks'];p['scenarios'][1]['id']=p['scenarios'][0]['id']
  with self.assertRaises(ValueError):r.joint_shocks(p)
 def test_no_leveraged_joint(self):
  p=self.fixture()['jointShocks'];p['base']['unleveredLinear']=False
  with self.assertRaises(ValueError):r.joint_shocks(p)
 def test_cost_can_reverse_shape(self):
  p=self.fixture()['localResponse'];self.assertEqual(r.local_response(p)['sampledShape'],'sampled-concave');p['points'][2]['cost']=0;self.assertEqual(r.local_response(p)['sampledShape'],'sampled-convex')
 def test_nonuniform_spacing(self):
  p=self.fixture()['localResponse'];p['points']=[dict(shock=x,grossPayoff=x*x,cost=0) for x in [0,1,3]];self.assertEqual(r.local_response(p)['rightSlope'],4)
 def test_linear_is_not_antifragile(self):
  p=self.fixture()['localResponse'];p['points']=[dict(shock=x,grossPayoff=x,cost=0) for x in [0,1,2]];v=r.local_response(p);self.assertEqual(v['sampledShape'],'sampled-linear-within-tolerance');self.assertFalse(v['antifragilityCertified'])
 def test_shock_order(self):
  p=self.fixture()['localResponse'];p['points'][1]['shock']=0
  with self.assertRaises(ValueError):r.local_response(p)
 def test_no_implicit_tolerance(self):
  p=self.fixture()['localResponse'];p.pop('absoluteSlopeTolerance')
  with self.assertRaises(KeyError):r.local_response(p)
 def test_no_implicit_cost(self):
  p=self.fixture()['localResponse'];p['points'][0]['cost']=None
  with self.assertRaises(ValueError):r.local_response(p)
 def test_all_modules_registered(self):self.assertEqual(set(r.review(self.fixture())['results']),{'compoundPath','cashConstraints','jointShocks','localResponse'})
if __name__=='__main__':unittest.main()
