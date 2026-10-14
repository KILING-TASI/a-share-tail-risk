import unittest,json,sys,copy,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from market_contract import assess
class Market(unittest.TestCase):
 def setUp(self):self.d=json.loads((ROOT/'examples/synthetic-contract.json').read_text());self.day='2026-10-14'
 def gate(self,k):return assess(self.d,self.day)['gates'][k]['status']
 def test_breadth_valid(self):self.assertEqual(self.gate('continuousBreadth'),'conditional')
 def test_empty_refuses(self):self.assertEqual(assess({},self.day)['gates']['wholeMarketState']['status'],'refused')
 def test_stale(self):self.d['asOf']='2026-10-13';self.assertEqual(self.gate('continuousBreadth'),'refused')
 def test_gap(self):self.d['expectedSessions'].pop();self.assertEqual(self.gate('continuousBreadth'),'refused')
 def test_pool_change(self):self.d['breadthHistory'][0]['poolId']='other';self.assertEqual(self.gate('continuousBreadth'),'refused')
 def test_unknown_method(self):self.d['breadthHistory'][0]['methodVerified']=False;self.assertEqual(self.gate('continuousBreadth'),'refused')
 def test_denominator(self):
  self.d['breadthHistory'][0]['total']=101
  with self.assertRaises(ValueError):assess(self.d,self.day)
 def test_duplicate(self):
  self.d['breadthHistory'][1]['date']=self.d['breadthHistory'][0]['date']
  with self.assertRaises(ValueError):assess(self.d,self.day)
 def test_wrong_unit(self):self.d['coverage']['SZSE']['unit']='CNY';self.assertEqual(self.gate('wholeMarketTurnover'),'refused')
 def test_missing_bse(self):del self.d['coverage']['BSE'];self.assertEqual(self.gate('wholeMarketTurnover'),'refused')
 def test_zero_not_unknown(self):self.assertEqual(self.gate('exitPressure'),'conditional')
 def test_missing_exit(self):self.d['exitPressure']['suspended']=None;self.assertEqual(self.gate('exitPressure'),'refused')
 def test_partial_exit(self):self.d['exitPressure']['reported']=99;self.assertEqual(self.gate('exitPressure'),'refused')
 def test_bool_expected(self):self.d['exitPressure']['expected']=True;self.d['exitPressure']['reported']=True;self.assertEqual(self.gate('exitPressure'),'refused')
 def test_source_injection(self):
  self.d['sources']=[{'url':'javascript:alert(1)'}]
  with self.assertRaises(ValueError):assess(self.d,self.day)
 def test_frozen_render(self):
  with tempfile.TemporaryDirectory() as td:
   dst=Path(td)/'view.html';args=[sys.executable,str(ROOT/'tools/render_dashboard.py'),'--input',str(ROOT/'examples/empty-market.json'),'--session',self.day,'--output',str(dst)]
   self.assertEqual(subprocess.run(args,capture_output=True).returncode,0);before=dst.read_bytes();self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0);self.assertEqual(before,dst.read_bytes());self.assertNotIn('__APP__',dst.read_text(encoding="utf-8"))

 def test_offline_refresh_records_failures(self):
  import update_market as u
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as td:
   out=Path(td)/'new';args=['update','--input',str(ROOT/'examples/empty-market.json'),'--session',self.day,'--output',str(out)]
   with patch.object(sys,'argv',args),patch.object(u,'request',side_effect=OSError('offline')):u.main()
   data=json.loads((out/'market-data.json').read_text(encoding='utf-8'));self.assertIsNone(data['asOf']);self.assertEqual(data['coverage']['SSE']['status'],'unavailable');self.assertEqual(data['assessment']['gates']['wholeMarketState']['status'],'refused')
 def test_sparse_xlsx_columns(self):
  import update_market as u,io,zipfile
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row><c r="A1" t="inlineStr"><is><t>类别</t></is></c><c r="C1"><v>12</v></c></row></sheetData></worksheet>')
  self.assertEqual(u.xlsx_rows(b.getvalue()),[['类别','','12']])
