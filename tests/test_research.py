import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skill/scripts'))
from research_summary import summarize
class Research(unittest.TestCase):
 def fixture(self):
  import datetime
  days=[str(datetime.date(2026,1,1)+datetime.timedelta(days=i)) for i in range(70)]
  h=[{'date':d,'value':100+i} for i,d in enumerate(days)]
  return {'records':[{'id':i,'assetClass':'test','history':h,'tier':'secondary','date':days[-1]} for i in ['sh000300','sh000905','sh000852']]}
 def test_matching_endpoints(self):r=summarize(self.fixture())['rows'][0];self.assertAlmostEqual(r['changes']['20'],169/149-1)
 def test_no_full_market_claim(self):self.assertEqual(summarize(self.fixture())['indexSample'],3)
 def test_missing_endpoint_unknown(self):d=self.fixture();d['records'][1]['history']=d['records'][1]['history'][:-1];self.assertIsNone(summarize(d)['rows'][1]['changes']['20'])
 def test_no_secondary_prices_published(self):d=self.fixture();d['records'][0]['value']=169;self.assertIsNone(summarize(d)['rows'][0]['level'])
 def test_constant_corr_unknown(self):d=self.fixture();d['records'][1]['history']=[dict(x,value=100) for x in d['records'][1]['history']];self.assertIsNone(summarize(d)['pairs'][0]['correlation'])
 def test_rates_not_price_returns(self):d=self.fixture();d['records'][0]['kind']='rate';self.assertIsNone(summarize(d)['rows'][0]['changes']['20'])
 def test_insufficient_drawdown(self):d=self.fixture();d['records'][0]['history']=d['records'][0]['history'][-20:];self.assertIsNone(summarize(d)['rows'][0]['drawdown60'])
 def test_empty(self):self.assertEqual(summarize({})['indexSample'],0)
