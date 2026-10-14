"""Bounded public-source refresh. Failures remain explicit; no authentication bypass."""
import sys,argparse,hashlib,io,json,re,urllib.request,urllib.parse,zipfile
import xml.etree.ElementTree as E
from datetime import date,datetime,timezone
from pathlib import Path
from market_contract import assess
def request(url):
    headers={'User-Agent':'Mozilla/5.0'}
    if urllib.parse.urlparse(url).hostname=='query.sse.com.cn':headers['Referer']='https://www.sse.com.cn/'
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=20) as response:return response.read()
def xlsx_rows(raw):
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        shared=[''.join(x.itertext()) for x in E.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)] if 'xl/sharedStrings.xml' in z.namelist() else []
        rows=[]
        for r in E.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//m:row',ns):
            vals=[]
            for c in r.findall('m:c',ns):
                col=re.match(r'[A-Z]+',c.get('r','A1')).group();pos=0
                for letter in col:pos=pos*26+ord(letter)-64
                while len(vals)<pos-1:vals.append('')
                v=c.find('m:v',ns);text=v.text if v is not None else ''.join(c.itertext());vals.append(shared[int(text)] if c.get('t')=='s' else text)
            rows.append(vals)
        return rows
def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--session',required=True);ap.add_argument('--output',required=True);ap.add_argument('--sz-date-proof');a=ap.parse_args();date.fromisoformat(a.session)
    print('开始核验官方统计；访问失败将保留缺口。',flush=True)
    output=Path(a.output)
    if output.exists():raise FileExistsError('use a new snapshot version; refusing overwrite')
    data=json.loads(Path(a.input).read_text(encoding='utf-8'));assess(data,a.session);output.mkdir(parents=True);events=[];coverage={m:dict(status='unavailable',reason='refresh failed or record not verified') for m in ('SSE','SZSE','BSE')};retrieved=datetime.now(timezone.utc).isoformat()
    def fetch(label,url):
        print('正在核验 '+label,flush=True)
        try:
            raw=request(url);(output/(label+'.raw')).write_bytes(raw);events.append(dict(source=label,url=url,status='retrieved',sha256=hashlib.sha256(raw).hexdigest(),retrievedAt=retrieved));return raw
        except Exception as e:events.append(dict(source=label,url=url,status='failed',error=type(e).__name__,retrievedAt=retrieved));return None
    u='https://query.sse.com.cn/commonQuery.do?'+urllib.parse.urlencode(dict(sqlId='COMMON_SSE_SJ_GPSJ_CJGK_MRGK_C',PRODUCT_CODE='01,02,03,11,17',type='inParams',SEARCH_DATE=a.session));raw=fetch('SSE',u)
    if raw:
        try:
            j=json.loads(raw);rows={r['PRODUCT_CODE']:r for r in j['result']}
            if any(rows[k]['TRADE_DATE']!=a.session.replace('-','') for k in ('01','03')):raise ValueError('response date mismatch')
            x,y=rows['01'],rows['03'];row=dict(date=a.session,turnoverA=float(x['TRADE_AMT']),turnoverStar=float(y['TRADE_AMT']),turnover=float(x['TRADE_AMT'])+float(y['TRADE_AMT']),peA=float(x['AVG_PE_RATE']),peStar=float(y['AVG_PE_RATE']),turnoverRateA=float(x['NEGO_TO_RATE']),turnoverRateStar=float(y['NEGO_TO_RATE']))
            data['sse']=sorted([r for r in data.get('sse',[]) if r['date']!=a.session]+[row],key=lambda r:r['date']);coverage['SSE']=dict(status='verified-snapshot',date=a.session,securityScope='A-share',unit='CNY-100m',turnover=row['turnover'])
        except Exception as e:coverage['SSE']=dict(status='date-or-format-unconfirmed',error=str(e))
    u='https://www.szse.cn/api/report/ShowReport?'+urllib.parse.urlencode(dict(SHOWTYPE='xlsx',CATALOGID='1803_sczm',TABKEY='tab1',txtQueryDate=a.session));raw=fetch('SZSE',u)
    if raw:
        try:
            rows=xlsx_rows(raw);assert rows[0][2]=='成交金额(元)';lookup={r[0].strip():r for r in rows[1:]};value=sum(float(lookup[k][2].replace(',','')) for k in ('主板A股','创业板A股'))/1e8
            proof=json.loads(Path(a.sz_date_proof).read_text(encoding='utf-8')) if a.sz_date_proof else {}
            verified=proof.get('date')==a.session and proof.get('aShareAmountsCny100m')==[round(float(lookup[k][2].replace(',',''))/1e8,2) for k in ('主板A股','创业板A股')] and proof.get('source')=='https://www.szse.cn/market/overview/index.html'
            coverage['SZSE']=dict(status='verified-snapshot' if verified else 'requested-date-only',date=a.session,securityScope='A-share',unit='CNY-100m',turnover=value,reason='XLSX has no internal date; independent dated webpage/date and amount proof required')
        except Exception as e:coverage['SZSE']=dict(status='format-unconfirmed',error=str(e))
    u='https://www.bse.cn/static/statisticdata.html';raw=fetch('BSE',u);coverage['BSE']=dict(status='unavailable' if raw is None else 'unparsed',reason='no verified same-date A-share turnover')
    events.append(dict(source='continuous-breadth',status='permission-required',reason='No automated vendor extraction; load an authorised historical dataset with pool and methodology.'))
    data.update(coverage=coverage,refreshRequestedFor=a.session,refreshedAt=retrieved,updateEvents=events)
    # Never relabel old prices or broad data as a fresh full-market snapshot.
    data['assessment']=assess(data,a.session)
    (output/'market-data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(output/'update-log.json').write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(output),'wholeMarketState':data['assessment']['gates']['wholeMarketState'],'events':len(events)},ensure_ascii=False))
if __name__=='__main__':main()
