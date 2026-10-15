import copy,hashlib,json,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"skill/scripts"))
from response_archive import ResponseArchive

class Pipeline(unittest.TestCase):
 def test_capture_replay_without_transport(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'source';a=ResponseArchive(p,lambda u,post:b'first');self.assertEqual(a('https://example.com'),b'first');stamp=a.finish();b=ResponseArchive(p,replay=True);self.assertEqual(b('https://example.com'),b'first');self.assertEqual(b.finish(),stamp)
 def test_corrupt_response_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'source';a=ResponseArchive(p,lambda u,post:b'first');a('https://example.com');a.finish();next(p.glob('*.bin')).write_bytes(b'changed');self.assertRaises(ValueError,ResponseArchive(p,replay=True),'https://example.com')
 def test_unknown_request_no_network(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'source';a=ResponseArchive(p,lambda u,post:b'first');a.finish();self.assertRaises(ValueError,ResponseArchive(p,replay=True),'https://other.example.com')
 def test_failed_request_replayed_as_failure(self):
  def fail(u,post):raise OSError('fixture failure')
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'source';a=ResponseArchive(p,fail);self.assertRaises(OSError,a,'https://example.com');a.finish();self.assertRaises(OSError,ResponseArchive(p,replay=True),'https://example.com')
 def test_archive_cannot_overwrite(self):
  with tempfile.TemporaryDirectory() as td:self.assertRaises(FileExistsError,ResponseArchive,td)
 def test_repeated_url_preserves_versions(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'source';vals=iter([b'one',b'two']);a=ResponseArchive(p,lambda u,post:next(vals));a('https://example.com');a('https://example.com');a.finish();b=ResponseArchive(p,replay=True);self.assertEqual([b('https://example.com'),b('https://example.com')],[b'one',b'two'])
