# SPDX-License-Identifier: MIT
"""Local response bytes and verified offline replay; no network in replay mode."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path

PROTOCOL='research-response-archive/1'
MAX_BYTES=16*1024*1024

class ResponseArchive:
 def __init__(self,path,transport=None,replay=False):
  self.path=Path(path);self.transport=transport;self.replay=replay;self.cursors={}
  if replay:
   p=self.path/'archive.json'
   if p.is_symlink() or not p.is_file() or p.stat().st_size>MAX_BYTES:raise ValueError('archive index missing or unsafe')
   self.index=json.loads(p.read_text(encoding='utf-8'))
   if self.index.get('schemaVersion')!=PROTOCOL or not isinstance(self.index.get('requests'),list):raise ValueError('archive version mismatch')
  else:
   if self.path.exists():raise FileExistsError('use a new response archive directory')
   self.path.mkdir(parents=True);self.index={'schemaVersion':PROTOCOL,'retrievedAt':datetime.now(timezone.utc).isoformat(),'requests':[],'limits':'byte consistency only; not origin authenticity, publication vintage or redistribution permission'};self.save()
 def save(self):
  if not self.replay:(self.path/'archive.json').write_text(json.dumps(self.index,ensure_ascii=False,indent=2),encoding='utf-8')
 def finish(self):
  if not self.replay:self.index['retrievedAt']=datetime.now(timezone.utc).isoformat();self.index['complete']=True;self.save()
  elif self.index.get('complete') is not True:raise ValueError('archive capture was interrupted; replay not complete')
  return self.index['retrievedAt']
 def __call__(self,url,post=False):
  if self.replay:
   key=(url,bool(post));items=[x for x in self.index['requests'] if x.get('url')==url and x.get('post')==bool(post)];i=self.cursors.get(key,0)
   if i>=len(items):raise ValueError('request absent from frozen archive; no network fallback')
   row=items[i];self.cursors[key]=i+1
   if row['status']!='received':raise OSError(row.get('error','frozen request failed'))
   sha=row['sha256']
   if len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha) or row['file']!='response-'+sha+'.bin':raise ValueError('unsafe response identity')
   p=self.path/row['file']
   if p.is_symlink() or not p.is_file() or p.stat().st_size>MAX_BYTES:raise ValueError('response missing or unsafe')
   raw=p.read_bytes()
   if len(raw)!=row['byteCount'] or hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('response checksum mismatch')
   return raw
  row={'url':url,'post':bool(post)}
  try:
   raw=self.transport(url,post)
   if not isinstance(raw,bytes) or len(raw)>MAX_BYTES:raise ValueError('response must be bytes under 16MiB')
   sha=hashlib.sha256(raw).hexdigest();name='response-'+sha+'.bin';p=self.path/name
   if not p.exists():p.write_bytes(raw)
   row.update(status='received',file=name,sha256=sha,byteCount=len(raw));return raw
  except Exception as e:row.update(status='failed',error=type(e).__name__+': '+str(e));raise
  finally:self.index['requests'].append(row);self.save()
