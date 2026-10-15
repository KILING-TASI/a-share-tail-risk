"""Automatic selected-asset snapshots. Standard library; no trading or TLS bypass."""
import argparse,csv,hashlib,io,json,math,os,re,subprocess,sys,tempfile,urllib.request
from datetime import datetime,date,timezone,timedelta
from pathlib import Path
import xml.etree.ElementTree as ET

TRANSPORT_NOTES=[]

def value(v):
 if isinstance(v,bool) or v is None:raise ValueError('boolean or missing number')
 x=float(v)
 if not math.isfinite(x):raise ValueError('non-finite value')
 return x

def iso(v):
 if not isinstance(v,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',v):raise ValueError('date must be YYYY-MM-DD')
 date.fromisoformat(v);return v

def fetch(url,post=False):
 req=urllib.request.Request(url,data=b'' if post else None,headers={'User-Agent':'Mozilla/5.0','Referer':'https://finance.sina.com.cn/' if 'sinajs.cn' in url else url})
 try:
  with urllib.request.urlopen(req,timeout=15) as r:return r.read()
 except urllib.error.URLError as e:
  # Native Windows trusted HTTPS, not an unverified SSL context.
  if os.name!='nt' or 'CERTIFICATE_VERIFY_FAILED' not in str(e) or url!='https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml':raise
  TRANSPORT_NOTES.append({'source':'ECB','reason':str(e),'fallback':'Windows trusted HTTPS; certificate verification remains enabled'})
  with tempfile.TemporaryDirectory() as td:
   dst=Path(td)/'fx.xml';quoted=str(dst).replace("'","''")
   cmd="$ErrorActionPreference='Stop'; Invoke-WebRequest -Uri 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml' -OutFile '"+quoted+"' -TimeoutSec 15"
   subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',cmd],check=True,timeout=25,capture_output=True)
   return dst.read_bytes()

def tencent(raw,symbol):
 m=re.search(r'v_'+re.escape(symbol)+r'="([^";]*)"',raw.decode('gb18030'))
 if not m:raise ValueError('symbol absent')
 x=m[1].split('~')
 if len(x)<33 or x[2]!=symbol[2:]:raise ValueError('symbol or quote structure mismatch')
 stamp=datetime.strptime(x[30],'%Y%m%d%H%M%S').isoformat()
 return {'name':x[1],'value':value(x[3]),'previousClose':value(x[4]),'observedAt':stamp+'+08:00','date':stamp[:10],'currency':'CNY','unit':'元/份或股','kind':'quote','basis':'数据商报价，非成交承诺'}

def sina(raw,symbol):
 m=re.search(r'hq_str_'+re.escape(symbol)+r'="([^";]*)"',raw.decode('gb18030'))
 if not m:raise ValueError('symbol absent')
 x=m[1].split(',')
 if len(x)<32:raise ValueError('quote structure mismatch')
 return {'name':x[0],'value':value(x[3]),'previousClose':value(x[2]),'date':iso(x[30]),'observedAt':x[30]+'T'+x[31]+'+08:00','currency':'CNY','unit':'元/份或股','kind':'quote','basis':'数据商报价，非成交承诺'}

def nav(raw,cutoff):
 text=raw.decode('utf-8');m=re.search(r'var Data_netWorthTrend\s*=\s*(\[.*?\]);',text)
 if not m:raise ValueError('published unit NAV history absent; estimates are not accepted')
 history=[]
 for row in json.loads(m[1]):
  dt=datetime.fromtimestamp(value(row['x'])/1000,timezone(timedelta(hours=8))).date().isoformat()
  if dt<=cutoff:history.append({'date':dt,'value':value(row['y'])})
 history.sort(key=lambda r:r['date'])
 if not history or any(r['value']<=0 for r in history):raise ValueError('NAV absent or invalid')
 name=re.search(r'var fS_name\s*=\s*("[^"]*")',text)
 return {'name':json.loads(name.group(1)) if name else '基金公布净值','value':history[-1]['value'],'date':history[-1]['date'],'currency':'CNY','unit':'单位净值','kind':'nav','history':history[-120:],'basis':'二手披露净值，需回查管理人；非盘中估算，非含分红总收益'}

def price_history(raw,symbol,cutoff):
 data=json.loads(raw)['data'][symbol];rows=data.get('qfqday') or data.get('day') or []
 result=[{'date':iso(x[0]),'value':value(x[2])} for x in rows if x[0]<=cutoff]
 if not result or any(x['value']<=0 for x in result):raise ValueError('dated closing-price history absent')
 if any(a['date']>=b['date'] for a,b in zip(result,result[1:])):raise ValueError('history duplicate or unordered')
 return result

def fx(raw,cutoff):
 rows=[]
 for n in ET.fromstring(raw).iter():
  if 'time' not in n.attrib:continue
  day=iso(n.attrib['time']);rates={c.attrib['currency']:value(c.attrib['rate']) for c in n if 'currency' in c.attrib}
  if day<=cutoff and all(k in rates for k in ('CNY','USD','JPY','GBP')):
   if any(v<=0 for v in rates.values()):raise ValueError('invalid FX rate')
   rows.append({'date':day,'EUR/CNY':rates['CNY'],'USD/CNY':rates['CNY']/rates['USD'],'JPY/CNY':rates['CNY']/rates['JPY'],'GBP/CNY':rates['CNY']/rates['GBP']})
 if not rows:raise ValueError('FX observations absent before cutoff')
 return sorted(rows,key=lambda r:r['date'])

def gold(raw,cutoff):
 text=re.sub(r'<!--.*?-->','',raw.decode('utf-8'),flags=re.S)
 for tr in re.findall(r'<tr[^>]*>(.*?)</tr>',text,re.S):
  cells=[re.sub(r'<[^>]+>','',c).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)]
  if len(cells)>6 and cells[0]==cutoff and cells[1]=='Au99.99':return {'name':'上金所Au99.99','date':iso(cells[0]),'value':value(cells[5]),'currency':'CNY','unit':'元/克','kind':'gold','basis':'指定合约收盘，不等于金饰零售价格'}
 raise ValueError('dated Au99.99 close absent')

def collect(manifest,cutoff,transport=fetch,progress=None):
 iso(cutoff);records=[];events=[];TRANSPORT_NOTES.clear()
 def get(label,url,parser,post=False):
  if progress:progress('正在核验 '+label)
  try:
   raw=transport(url,post);r=parser(raw)
   if isinstance(r,list) and not r:raise ValueError('no dated observations')
   items=r if isinstance(r,list) else [r]
   for item in items:
    if item.get('date') and item['date']>cutoff:raise ValueError('observation after requested cutoff')
    if item.get('kind') in ('quote','nav','gold') and item.get('value') is not None and item['value']<=0:raise ValueError('nonpositive asset price')
   events.append({'source':label,'url':url,'status':'success','sha256':hashlib.sha256(raw).hexdigest()});return r
  except Exception as e:events.append({'source':label,'url':url,'status':'failed','error':str(e)});return None
 symbols=manifest.get('securities',[])
 if len(manifest.get('funds',[]))>50 or len(set(manifest.get('funds',[])))!=len(manifest.get('funds',[])):raise ValueError('use at most 50 distinct funds per snapshot')
 if len(symbols)>50 or len(set(x['symbol'] for x in symbols))!=len(symbols):raise ValueError('request 1-50 distinct selected securities per snapshot')
 for spec in symbols:
  sym=spec['symbol']
  if not re.fullmatch(r'(sh|sz|bj)\d{6}',sym):raise ValueError('invalid symbol')
  rec=None
  for label,url,parser in [('腾讯','https://qt.gtimg.cn/q='+sym,tencent),('新浪','https://hq.sinajs.cn/list='+sym,sina)]:
   rec=get(label+' '+sym,url,lambda b:parser(b,sym))
   if rec:rec.update(source=label,sourceUrl=url);break
  histurl='https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param='+sym+',day,,,120,qfq'
  history=get('腾讯历史行情 '+sym,histurl,lambda b:price_history(b,sym,cutoff))
  if rec is None and history:
   rec={'name':spec.get('name',sym),'value':history[-1]['value'],'date':history[-1]['date'],'currency':'CNY','kind':'quote','source':'腾讯历史收盘','sourceUrl':histurl,'basis':'按截止日取历史收盘，非当前报价'}
  if rec:
   if history:rec['history']=history;rec['historySourceUrl']=histurl;rec['historyBasis']='本次前复权/指数价格版本，非含分红全收益，不认证历史时点可得性'
   rec['unit']='点' if spec['assetClass']=='股票指数' else ('元/股' if spec['assetClass']=='股票' else '元/份')
   if manifest.get('crossCheck',True) and rec['source'] in ('腾讯','新浪'):
    otherSource='新浪' if rec['source']=='腾讯' else '腾讯'
    otherUrl=('https://hq.sinajs.cn/list=' if otherSource=='新浪' else 'https://qt.gtimg.cn/q=')+sym
    otherParser=sina if otherSource=='新浪' else tencent
    other=get(otherSource+'交叉核验 '+sym,otherUrl,lambda b:otherParser(b,sym))
    rec['crossCheck']={'otherSource':otherSource,'status':'consistent' if other and other['date']==rec['date'] and abs(other['value']-rec['value'])<=max(.0001,abs(rec['value'])*.000001) else ('divergent' if other else 'unavailable'),'otherValue':other['value'] if other else None,'otherDate':other['date'] if other else None,'note':'同日两商报价比较，不认证实时性、独立底层或来源真实'}
  records.append(dict(rec or {},id=sym,assetClass=spec['assetClass'],status='available' if rec else 'unavailable',tier='secondary',redistribution='permission-unconfirmed'))
 for code in manifest.get('funds',[]):
  if not re.fullmatch(r'\d{6}',code):raise ValueError('invalid fund code')
  url='https://fund.eastmoney.com/pingzhongdata/'+code+'.js';r=get('天天基金',url,lambda b:nav(b,cutoff));records.append(dict(r or {},id=code,name=(r or {}).get('name','基金'+code),assetClass='公募基金',status='available' if r else 'unavailable',tier='secondary',source='天天基金',sourceUrl=url,redistribution='permission-unconfirmed'))
 url='https://www.sge.com.cn/sjzx/quotation_daily_new?start_date='+cutoff+'&end_date='+cutoff;r=get('上海黄金交易所',url,lambda b:gold(b,cutoff));records.append(dict(r or {},id='SGE-Au9999',assetClass='黄金现货合约',status='available' if r else 'unavailable',tier='primary',sourceUrl=url))
 url='https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml';r=get('欧洲央行',url,lambda b:fx(b,cutoff))
 for pair in ('EUR/CNY','USD/CNY','JPY/CNY','GBP/CNY'):
  records.append(dict(id=pair,name=pair,assetClass='外汇参考汇率',status='available' if r else 'unavailable',tier='primary',sourceUrl=url,**({'value':r[-1][pair],'date':r[-1]['date'],'currency':'CNY','unit':'人民币/1单位外币','history':[{'date':x['date'],'value':x[pair]} for x in r],'basis':'ECB参考汇率及同日交叉换算，非国内银行成交价'} if r else {})))
 url='https://www.chinamoney.com.cn/ags/ms/cm-u-bk-shibor/ShiborHis?startDate='+str(date.fromisoformat(cutoff)-timedelta(days=120))+'&endDate='+cutoff
 def shibor(b):
  rows=[{'date':iso(x['showDateCN']),'value':value(x['ON'])} for x in json.loads(b)['records'] if x['showDateCN']<=cutoff];return sorted(rows,key=lambda x:x['date'])
 r=get('中国货币网',url,shibor);records.append(dict(id='SHIBOR-ON',name='Shibor隔夜',assetClass='货币市场利率',status='available' if r else 'unavailable',tier='primary',sourceUrl=url,**({'date':r[-1]['date'],'value':r[-1]['value'],'unit':'%','kind':'rate','history':r,'basis':'银行间拆借参考利率，不是个人存款利率'} if r else {})))
 url='https://yield.chinabond.com.cn/cbweb-pbc-web/pbc/pbcInit?locale=zh_CN'
 def bonds(b):
  rows=json.loads(b);r=next(x for x in rows if x['ycDefName']=='中债国债收益率曲线');iso(r['worktime']);points=[{'years':value(x),'yieldPct':value(y)} for x,y in r['seriesData'] if x in (1,3,5,10,30)];return {'date':r['worktime'],'curve':points,'value':next(x['yieldPct'] for x in points if x['years']==10),'name':'中债国债10年','kind':'yield','unit':'%','basis':'接口worktime原样保留；曲线估值不是特定债券成交价'}
 r=get('中债',url,bonds,True);records.append(dict(r or {},id='CGB-10Y',assetClass='国债收益率',status='available' if r else 'unavailable',tier='primary',sourceUrl=url))
 for r in records:r['freshness']='same-date' if r.get('date')==cutoff else ('older-observation' if r.get('date') else 'unknown')
 return {'schemaVersion':'assets-v1','targetSession':cutoff,'retrievedAt':datetime.now(timezone.utc).isoformat(),'records':records,'events':events,'scope':'selected instruments and reference series, not entire market or personal assets','transportNotes':list(TRANSPORT_NOTES),'manualClasses':['存款合同利率','理财产品兑付和赎回条款','房地产与非上市股权估值','个人债务、担保与经营现金流']}

def merge_previous(current,previous):
 old={r['id']:r for r in previous.get('records',[])}
 for r in current['records']:
  prev=old.get(r['id'])
  if not prev:continue
  if r['status']=='unavailable' and prev.get('value') is not None and prev.get('date','')<=current['targetSession']:
   r.update({k:v for k,v in prev.items() if k not in ('status','freshness')});r['status']='stale-cache';r['freshness']='cached-not-refreshed';continue
  if r.get('historyBasis') and r.get('history'):continue
  if r['status']=='available' and prev.get('unit')==r.get('unit') and prev.get('currency')==r.get('currency'):
   points={x['date']:x for x in prev.get('history',[]) if x['date']<=current['targetSession']}
   if prev.get('date') and prev.get('value') is not None:points[prev['date']]={'date':prev['date'],'value':prev['value']}
   points.update({x['date']:x for x in r.get('history',[])})
   if r.get('date'):points[r['date']]={'date':r['date'],'value':r['value']}
   r['history']=sorted(points.values(),key=lambda x:x['date'])[-252:]
 return current

def main():
 if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--session',required=True);ap.add_argument('--output',required=True);ap.add_argument('--previous');a=ap.parse_args();out=Path(a.output)
 if out.exists():ap.exit(2,'禁止覆盖冻结快照，请使用新文件名。\n')
 print('开始自动核验所选资产、官方黄金、利率和汇率。失败保留原因。',flush=True)
 data=collect(json.loads(Path(a.manifest).read_text(encoding='utf-8')),a.session,progress=lambda text:print(text,flush=True))
 if a.previous:data=merge_previous(data,json.loads(Path(a.previous).read_text(encoding='utf-8')))
 out.parent.mkdir(parents=True,exist_ok=True);
 with out.open('x',encoding='utf-8') as f:f.write(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False))
 print('完成：'+str(sum(r['status']=='available' for r in data['records']))+'/'+str(len(data['records']))+' 记录可用；'+str(out))
if __name__=='__main__':main()
