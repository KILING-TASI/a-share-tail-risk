import unittest,json,sys,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'skill/scripts'))
import collect_assets as c
class Collect(unittest.TestCase):
 def test_tencent_identity(self):
  x=['0']*33;x[1]='测试';x[2]='600000';x[3]='10';x[4]='9';x[30]='20261014150000';r=c.tencent(('v_sh600000="'+'~'.join(x)+'";').encode('gb18030'),'sh600000');self.assertEqual(r['value'],10);self.assertEqual(r['date'],'2026-10-14')
 def test_bad_symbol(self):
  with self.assertRaises(ValueError):c.tencent(b'v_sh600000="x";','sh600000')
 def test_nav_not_estimate(self):
  with self.assertRaises(ValueError):c.nav(b'jsonpgz({"gsz":10})','2026-10-14')
 def test_nav_cutoff(self):
  raw=b'var Data_netWorthTrend=[{"x":1791907200000,"y":1.2},{"x":1791993600000,"y":1.3}];';self.assertEqual(c.nav(raw,'2026-10-14')['value'],1.2)
 def test_no_js_execution(self):
  with self.assertRaises(ValueError):c.nav(b'var Data_netWorthTrend=evil();','2026-10-14')
 def test_fx_cross_rate(self):
  r=c.fx(b'<Cube><Cube time="2026-10-14"><Cube currency="CNY" rate="8"/><Cube currency="USD" rate="2"/><Cube currency="JPY" rate="100"/><Cube currency="GBP" rate="1"/></Cube></Cube>','2026-10-14');self.assertEqual(r[0]['USD/CNY'],4)
 def test_fx_zero_denominator(self):
  with self.assertRaises(ValueError):c.fx(b'<Cube><Cube time="2026-10-14"><Cube currency="CNY" rate="8"/><Cube currency="USD" rate="0"/><Cube currency="JPY" rate="100"/><Cube currency="GBP" rate="1"/></Cube></Cube>','2026-10-14')
 def test_gold_close_not_open(self):
  r=c.gold(b'<tr><td>2026-10-14</td><td>Au99.99</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td></tr>','2026-10-14');self.assertEqual(r['value'],4)
 def test_gold_date_mismatch(self):
  with self.assertRaises(ValueError):c.gold(b'<tr><td>2026-10-13</td><td>Au99.99</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td></tr>','2026-10-14')
 def test_all_failures_explicit(self):
  def fail(*args):raise OSError('offline')
  d=c.collect({'securities':[],'funds':[]},'2026-10-14',fail);self.assertTrue(all(r['status']=='unavailable' for r in d['records']));self.assertTrue(all(e['status']=='failed' for e in d['events']))
 def test_cache_failure_not_fresh(self):
  old={'records':[{'id':'a','value':1,'date':'2026-10-13','status':'available','unit':'CNY'}]};new={'targetSession':'2026-10-14','records':[{'id':'a','status':'unavailable'}]};r=c.merge_previous(new,old)['records'][0];self.assertEqual(r['status'],'stale-cache');self.assertEqual(r['date'],'2026-10-13')
 def test_future_cache_not_used(self):
  old={'records':[{'id':'a','value':1,'date':'2026-10-15'}]};new={'targetSession':'2026-10-14','records':[{'id':'a','status':'unavailable'}]};self.assertNotIn('value',c.merge_previous(new,old)['records'][0])
 def test_unit_change_no_merge(self):
  old={'records':[{'id':'a','value':1,'date':'2026-10-13','unit':'USD','currency':'USD'}]};new={'targetSession':'2026-10-14','records':[{'id':'a','value':2,'date':'2026-10-14','unit':'CNY','currency':'CNY','status':'available'}]};self.assertNotIn('history',c.merge_previous(new,old)['records'][0])
 def test_url_injection_symbol(self):
  with self.assertRaises(ValueError):c.collect({'securities':[{'symbol':'sh600000&x=1','assetClass':'股票'}]},'2026-10-14',lambda *a:b'')

 def test_boolean_quote_value(self):
  with self.assertRaises(ValueError):c.value(True)

 def test_fallback_not_self_crosscheck(self):
  x=['0']*32;x[0]='测试';x[2]='9';x[3]='10';x[30]='2026-10-14';x[31]='15:00:00';raw=('var hq_str_sh600000="'+','.join(x)+'";').encode('gb18030')
  def transport(url,post):
   if 'sinajs' in url:return raw
   raise OSError('offline')
  d=c.collect({'securities':[{'symbol':'sh600000','assetClass':'股票'}]},'2026-10-14',transport);r=d['records'][0];self.assertEqual(r['source'],'新浪');self.assertEqual(r['crossCheck']['status'],'unavailable');self.assertEqual(r['crossCheck']['otherSource'],'腾讯')

 def test_historical_close_when_live_quote_is_newer(self):
  def transport(url,post):
   if 'fqkline' in url:return json.dumps({'data':{'sh600000':{'qfqday':[['2026-10-14','9','10','11','8','100']]}}}).encode()
   raise OSError('live not available for requested date')
  r=c.collect({'securities':[{'symbol':'sh600000','assetClass':'股票','name':'测试'}]},'2026-10-14',transport)['records'][0];self.assertEqual(r['value'],10);self.assertEqual(r['date'],'2026-10-14');self.assertEqual(r['source'],'腾讯历史收盘')
