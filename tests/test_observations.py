import unittest,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skill/scripts'))
from build_observations import derive
class Observations(unittest.TestCase):
 def setUp(self):self.meta={'expectedSessions':['2026-10-14'],'poolCodes':['a','b'],'poolId':'test','ruleVersion':'test','methodVerified':True};self.rows=[{'date':'2026-10-14','code':k,'close':'9','prevClose':'10','volume':'0','status':'trading','limitDown':'9'} for k in ['a','b']]
 def test_counts(self):r=derive(self.rows,self.meta);self.assertEqual(r['breadth']['down'],2);self.assertEqual(r['exitPressure']['downLimit'],2)
 def test_overlap_not_added(self):r=derive(self.rows,self.meta)['exitPressure'];self.assertEqual(r['zeroVolumeDown'],2);self.assertEqual(r['expected'],2)
 def test_missing_pool(self):
  with self.assertRaises(ValueError):derive(self.rows[:1],self.meta)
 def test_duplicate(self):
  with self.assertRaises(ValueError):derive(self.rows*2,self.meta)
 def test_unknown_limit(self):self.rows[0]['limitDown']='';self.assertIsNone(derive(self.rows,self.meta)['exitPressure']['downLimit'])
 def test_unknown_status(self):
  self.rows[0]['status']='unknown'
  with self.assertRaises(ValueError):derive(self.rows,self.meta)
 def test_outside_calendar(self):
  self.rows[0]['date']='2026-10-13'
  with self.assertRaises(ValueError):derive(self.rows,self.meta)
 def test_negative_volume(self):
  self.rows[0]['volume']='-1'
  with self.assertRaises(ValueError):derive(self.rows,self.meta)
