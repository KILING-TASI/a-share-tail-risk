"""Multi-region annual macro context. Latest revised series, never a PIT backtest."""
import argparse,hashlib,json,math,urllib.parse
from datetime import datetime,date,timezone
from pathlib import Path
from collect_assets import fetch
from data_matcher import deduplicate

INDICATORS={
 'NY.GDP.MKTP.KD.ZG':('实际GDP增速','annual-percent'),
 'FP.CPI.TOTL.ZG':('居民消费价格通胀','annual-percent'),
 'SL.UEM.TOTL.ZS':('失业率（ILO模型估计）','percent-labour-force'),
 'NV.IND.MANF.ZS':('制造业增加值占GDP','percent-GDP'),
 'NE.EXP.GNFS.ZS':('货物和服务出口占GDP','percent-GDP'),
 'FM.LBL.BMNY.GD.ZS':('广义货币占GDP','percent-GDP')}

def parse_worldbank(raw,indicator,regions,start,end,url,retrieved):
 from wdi_core import parse
 meta,rows=parse(raw,dict(countries=regions,indicator=indicator,start=start,end=end),1)
 if meta['pages']!=1 or len(rows)!=int(meta['total']):raise ValueError('context request requires complete single page')
 records=[];missing=0
 for r in rows:
  if r['value'] is None:missing+=1;continue
  v=float(r['value'])
  if not math.isfinite(v):raise ValueError('macro numeric overflow')
  records.append({'entityId':r['regionCode'],'metric':indicator,'name':INDICATORS[indicator][0],'sourceMetricName':r['indicatorName'],'region':r['regionCode'],'frequency':'annual','period':r['period'],'value':v,'sourceDecimalText':r['value'],'unit':INDICATORS[indicator][1],'currency':None,'basis':'World Bank WDI latest revised version; not historical release vintage','sourceUrl':url,'source':'World Bank WDI','sourceUpdateDate':meta.get('lastupdated'),'retrievedAt':retrieved,'availableAt':None,'version':meta.get('lastupdated'),'footnote':r['footnote']})
 return records,missing

def collect(config,cutoff,transport=fetch,progress=None):
 date.fromisoformat(cutoff);start=config.get('startYear',2010);end=min(config.get('endYear',date.fromisoformat(cutoff).year-1),date.fromisoformat(cutoff).year-1);regions=config['regions'];indicators=config['indicators']
 if isinstance(start,bool) or not isinstance(start,int) or not 1960<=start<=end:raise ValueError('invalid year range')
 if not 1<=len(regions)<=20 or len(set(regions))!=len(regions) or any(not isinstance(x,str) or len(x)!=3 or not x.isalpha() or x!=x.upper() for x in regions):raise ValueError('use 1-20 distinct ISO3 regions')
 if not indicators or len(set(indicators))!=len(indicators) or any(x not in INDICATORS for x in indicators):raise ValueError('unsupported or duplicate indicator')
 retrieved=datetime.now(timezone.utc).isoformat();records=[];events=[]
 for code in indicators:
  url='https://api.worldbank.org/v2/country/'+';'.join(regions)+'/indicator/'+code+'?'+urllib.parse.urlencode({'date':str(start)+':'+str(end),'format':'json','per_page':20000})
  if progress:progress('正在采集多国年度指标：'+INDICATORS[code][0])
  try:
   raw=transport(url);rows,missing=parse_worldbank(raw,code,regions,start,end,url,retrieved);records+=rows;events.append({'indicator':code,'sourceUrl':url,'status':'success','records':len(rows),'nullObservations':missing,'sha256':hashlib.sha256(raw).hexdigest()})
  except Exception as e:events.append({'indicator':code,'sourceUrl':url,'status':'failed','error':str(e)})
 # An explicit first-party provincial request, with no challenge/login bypass.
 if config.get('probeChinaProvinces'):
  url='https://data.stats.gov.cn/easyquery.htm?'+urllib.parse.urlencode({'m':'QueryData','dbcode':'fsnd','rowcode':'reg','colcode':'sj','wds':json.dumps([{'wdcode':'zb','valuecode':'A020101'}]),'dfwds':json.dumps([{'wdcode':'sj','valuecode':'LAST20'}])})
  try:
   raw=transport(url);events.append({'sourceUrl':url,'status':'unverified-response','sha256':hashlib.sha256(raw).hexdigest(),'reason':'provincial indicator labels and units require adapter verification; not ingested'})
  except Exception as e:events.append({'sourceUrl':url,'status':'failed','error':str(e),'scope':'China provinces; no observations ingested'})
 clean=deduplicate(records);coverage=[]
 for region in regions:
  for indicator in indicators:
   rows=[r for r in clean['records'] if r['region']==region and r['metric']==indicator];years={int(r['period']) for r in rows}
   coverage.append({'region':region,'indicator':indicator,'name':INDICATORS[indicator][0],'availableYears':len(years),'firstYear':min(years) if years else None,'lastYear':max(years) if years else None,'missingYears':[y for y in range(start,end+1) if y not in years],'status':'available' if rows else 'missing'})
 return {'schemaVersion':'context-v1','asOf':cutoff,'retrievedAt':retrieved,'requestedStartYear':start,'requestedEndYear':end,'regions':regions,'records':clean['records'],'conflicts':clean['conflicts'],'coverage':coverage,'events':events,'limits':'annual macro context, mixed release lag and revisions; no daily market state, causal proof, micro issuer coverage or point-in-time availability certification'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--session',required=True);p.add_argument('--output',required=True);p.add_argument('--replay-archive');a=p.parse_args();out=Path(a.output)
 if out.exists():p.exit(2,'禁止覆盖冻结结果，请使用新文件名。\n')
 from response_archive import ResponseArchive
 archive=ResponseArchive(a.replay_archive or str(out)+'.sources',transport=fetch,replay=bool(a.replay_archive))
 d=collect(json.loads(Path(a.manifest).read_text(encoding='utf-8')),a.session,transport=archive,progress=lambda text:print(text,flush=True))
 d['sourceArchive']={'schemaVersion':'research-response-archive/1','directory':str(archive.path),'offlineReplay':bool(a.replay_archive)}
 d['retrievedAt']=archive.finish()
 if a.replay_archive:d['replayedAt']=datetime.now(timezone.utc).isoformat()
 for row in d['records']:row['retrievedAt']=d['retrievedAt']
 out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,allow_nan=False,indent=2)
 print('完成：'+str(len(d['records']))+'条年度观察；'+str(sum(c['status']=='available' for c in d['coverage']))+'/'+str(len(d['coverage']))+'地区指标组合有数据。')
if __name__=='__main__':main()
