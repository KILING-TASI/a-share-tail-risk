import unittest,sys,json,copy,urllib.error
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'skill/scripts'))
from data_matcher import match,deduplicate
from collect_context import collect,parse_worldbank
from collect_assets import fetch,merge_previous,price_history

class Matcher(unittest.TestCase):
 def setUp(self):self.a=dict(entityId='SSE:510300',shareClass='listed-unit',metric='market_price',region='CHN',frequency='daily',period='2026-10-14',value=1.05,unit='per-unit',currency='CNY',basis='unit-price',sourceUrl='https://example.com/test',availableAt=None);self.b=dict(self.a,metric='published_unit_nav',value=1)
 def test_matched_premium(self):self.assertAlmostEqual(match(self.a,self.b,'premium')['premium'],.05)
 def test_different_currency(self):self.b['currency']='USD';self.assertEqual(match(self.a,self.b,'premium')['status'],'rejected')
 def test_different_day(self):self.b['period']='2026-10-13';self.assertEqual(match(self.a,self.b,'premium')['status'],'rejected')
 def test_estimate_refused(self):self.b['metric']='estimated_nav';self.assertEqual(match(self.a,self.b,'premium')['status'],'rejected')
 def test_same_name_different_listing(self):self.b['entityId']='HKEX:510300';self.assertEqual(match(self.a,self.b,'premium')['status'],'rejected')
 def test_share_class(self):self.b['shareClass']='off-exchange';self.assertEqual(match(self.a,self.b,'premium')['status'],'rejected')
 def test_missing_share_class(self):self.a.pop('shareClass');self.b.pop('shareClass');self.assertEqual(match(self.a,self.b,'premium')['status'],'rejected')
 def test_unknown_vintage_refused(self):self.assertEqual(match(self.a,self.a,cutoff='2026-10-14',point_in_time=True)['status'],'rejected')
 def test_timezone_future(self):self.a['availableAt']='2026-10-14T23:00:00-04:00';self.assertEqual(match(self.a,self.a,cutoff='2026-10-14',point_in_time=True)['status'],'rejected')
 def test_known_release(self):self.a['availableAt']='2026-10-14T16:00:00+08:00';self.assertEqual(match(self.a,self.a,cutoff='2026-10-14',point_in_time=True)['status'],'conditional-match')
 def test_cross_frequency_no_fill(self):self.b.update(frequency='annual',period='2025');self.assertEqual(match(self.a,self.b,'premium')['status'],'rejected')
 def test_month_not_completed(self):a=dict(self.a,frequency='monthly',period='2026-10');self.assertEqual(match(a,a,cutoff='2026-10-14')['status'],'rejected')
 def test_duplicate_conflict_quarantined(self):r=deduplicate([self.a,dict(self.a,value=2),dict(self.a,value=3)]);self.assertEqual(r['records'],[]);self.assertEqual(len(r['conflicts']),1)
 def test_exact_duplicate_one(self):self.assertEqual(len(deduplicate([self.a,self.a])['records']),1)
 def test_no_unit_conversion(self):b=dict(self.a,unit='CNY-100m');self.assertEqual(match(self.a,b)['status'],'rejected')
 def test_cross_region_same_metric(self):b=dict(self.a,region='USA',entityId='USA');self.assertEqual(match(self.a,b,'cross-region')['status'],'conditional-match')

class Collection(unittest.TestCase):
 def fixture(self,value=2):return json.dumps([{'pages':1,'lastupdated':'2026-10-08'},[{'countryiso3code':'CHN','date':'2025','value':value,'indicator':{'id':'NY.GDP.MKTP.KD.ZG','value':'GDP growth'},'obs_status':''}]]).encode()
 def test_null_not_zero(self):r,n=parse_worldbank(self.fixture(None),'NY.GDP.MKTP.KD.ZG',['CHN'],2010,2025,'https://example.com','now');self.assertEqual(r,[]);self.assertEqual(n,1)
 def test_latest_revision_not_release_timestamp(self):r,n=parse_worldbank(self.fixture(),'NY.GDP.MKTP.KD.ZG',['CHN'],2010,2025,'https://example.com','now');self.assertIsNone(r[0]['availableAt'])
 def test_wrong_region_rejected(self):self.assertRaises(ValueError,parse_worldbank,self.fixture(),'NY.GDP.MKTP.KD.ZG',['USA'],2010,2025,'https://example.com','now')
 def test_pagination_rejected(self):raw=self.fixture().replace(b'"pages": 1',b'"pages": 2');self.assertRaises(ValueError,parse_worldbank,raw,'NY.GDP.MKTP.KD.ZG',['CHN'],2010,2025,'https://example.com','now')
 def test_failures_preserved(self):
  def fail(url):raise ValueError('failure fixture')
  r=collect({'regions':['CHN'],'indicators':['NY.GDP.MKTP.KD.ZG']},'2026-10-14',transport=fail);self.assertEqual(r['coverage'][0]['status'],'missing');self.assertEqual(r['events'][0]['status'],'failed')
 def test_full_requested_missing_years(self):r=collect({'regions':['CHN'],'indicators':['NY.GDP.MKTP.KD.ZG']},'2026-10-14',transport=lambda u:self.fixture());self.assertEqual(len(r['coverage'][0]['missingYears']),15)
 def test_403_never_retried(self):
  e=urllib.error.HTTPError('https://example.com',403,'denied',{},None)
  with patch('collect_assets._fetch_once',side_effect=e) as f:self.assertRaises(urllib.error.HTTPError,fetch,'https://example.com');self.assertEqual(f.call_count,1)
 def test_transient_retry_bounded(self):
  e=urllib.error.HTTPError('https://example.com',503,'unavailable',{},None)
  with patch('collect_assets._fetch_once',side_effect=e) as f,patch('collect_assets.time.sleep'):self.assertRaises(urllib.error.HTTPError,fetch,'https://example.com');self.assertEqual(f.call_count,3)
 def test_long_series_not_truncated_by_cache(self):
  h=[{'date':'synthetic','value':i} for i in range(800)];current={'records':[dict(id='fx',status='available',history=h)]};previous={'records':[dict(id='fx',history=[])]};self.assertEqual(len(merge_previous(current,previous)['records'][0]['history']),800)
 def test_ohlcv_preserved(self):
  raw=json.dumps({'data':{'sh1':{'day':[['2026-10-14','9','10','11','8','123']]}}}).encode();r=price_history(raw,'sh1','2026-10-14')[0];self.assertEqual(r['volume'],123);self.assertEqual(r['high'],11)
 def test_inconsistent_ohlc_rejected(self):
  raw=json.dumps({'data':{'sh1':{'day':[['2026-10-14','9','10','7','8','123']]}}}).encode();self.assertRaises(ValueError,price_history,raw,'sh1','2026-10-14')
 def test_negative_volume_rejected(self):
  raw=json.dumps({'data':{'sh1':{'day':[['2026-10-14','9','10','11','8','-1']]}}}).encode();self.assertRaises(ValueError,price_history,raw,'sh1','2026-10-14')
