"""Dataset scope and refusal gates. Metadata is declared, not authenticated."""
from datetime import date
import math,re
def real(v,minimum=0):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<minimum:raise ValueError('invalid finite numeric value')
    return v
def session_date(v):
    if not isinstance(v,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',v):raise ValueError('dates must be YYYY-MM-DD')
    return date.fromisoformat(v)

def dates(rows):
    parsed=[session_date(r['date']) for r in rows]
    if any(a>=b for a,b in zip(parsed,parsed[1:])):raise ValueError('duplicate or unordered dates')
    return parsed
def assess(d,target_session):
    target=session_date(target_session);out={}
    def gate(key,reasons):out[key]={'status':'refused' if reasons else 'conditional','reasons':reasons}
    asof=d.get('asOf');fresh=asof==target.isoformat()
    freshness=[] if fresh else ['snapshot date differs from selected completed trading session']
    dates(d.get('sse',[]));dates(d.get('csi300',[]))
    for r in d.get('sse',[]):
        for k in ('turnover','turnoverA','turnoverStar','peA','peStar','turnoverRateA','turnoverRateStar'):real(r[k])
    for r in d.get('csi300',[]):real(r['close'],.000001)
    for r in d.get('indices',[]):real(r['close'],.000001);real(r['change'],-100)
    for s in d.get('sources',[]):
        from urllib.parse import urlparse
        if urlparse(s['url']).scheme not in ('http','https'):raise ValueError('unsafe source URL')
    for key,rows in [('indexTrend',d.get('csi300',[])),('shanghaiVolume',d.get('sse',[]))]:
        reasons=freshness.copy()
        if len(rows)<6:reasons.append('fewer than six dated observations')
        if rows and rows[-1]['date']!=target_session:reasons.append('series end date does not match target')
        gate(key,reasons)
    cov=d.get('coverage',{})
    reasons=freshness.copy()
    for market in ('SSE','SZSE','BSE'):
        row=cov.get(market,{})
        if row.get('status')!='verified-snapshot' or row.get('date')!=target_session or row.get('unit')!='CNY-100m' or row.get('securityScope')!='A-share':reasons.append(market+' absent or scope/date/unit unconfirmed')
        elif row.get('turnover') is None:reasons.append(market+' turnover absent')
        else:real(row['turnover'])
    gate('wholeMarketTurnover',reasons)
    b=d.get('breadth');reasons=freshness.copy()
    if not b:reasons.append('breadth absent')
    else:
        for k in ('up','flat','down','total'):real(b[k])
        if any(int(b[k])!=b[k] for k in ('up','flat','down','total')):raise ValueError('breadth counts must be integer')
        if b['total']<=0 or b['up']+b['flat']+b['down']!=b['total']:raise ValueError('breadth denominator mismatch')
        if b.get('date')!=target_session:reasons.append('breadth date mismatch')
    gate('singleDayVendorBreadth',reasons)
    history=d.get('breadthHistory',[]);dates(history);reasons=freshness.copy()
    if len(history)<5:reasons.append('fewer than five breadth observations')
    expected=d.get('expectedSessions',[])
    if not expected or [r['date'] for r in history]!=expected:reasons.append('completed trading-session calendar absent or has gaps')
    if history and history[-1]['date']!=target_session:reasons.append('breadth end date mismatch')
    pool_ids=set()
    for row in history:
        for k in ('up','flat','down','total'):real(row[k])
        if any(int(row[k])!=row[k] for k in ('up','flat','down','total')) or row['total']<=0 or row['up']+row['flat']+row['down']!=row['total']:raise ValueError('historical breadth denominator mismatch')
        pool_ids.add(row.get('poolId'))
        if row.get('methodVerified') is not True:reasons.append('breadth inclusion method unverified')
    if None in pool_ids or '' in pool_ids or len(pool_ids)!=1:reasons.append('stock-pool identity changes or is unknown')
    gate('continuousBreadth',list(dict.fromkeys(reasons)))
    ex=d.get('exitPressure');reasons=freshness.copy()
    if not ex:reasons.append('suspension/limit/execution observations absent')
    else:
        if ex.get('date')!=target_session:reasons.append('exit-pressure date mismatch')
        if not ex.get('ruleVersion') or not ex.get('poolId') or ex.get('methodVerified') is not True:reasons.append('exit-pressure pool or rule method unverified')
        if ex.get('reported')!=ex.get('expected') or (not isinstance(ex.get('expected'),int) or isinstance(ex.get('expected'),bool)) or ex['expected']<=0:reasons.append('exit-pressure coverage incomplete')
        for k in ('downLimit','suspended','zeroVolumeDown'):
            if ex.get(k) is None:reasons.append(k+' absent')
            else:
                real(ex[k])
                if int(ex[k])!=ex[k] or ex[k]>ex.get('expected',0):raise ValueError('invalid exit count')
    gate('exitPressure',reasons)
    whole=sum((out[k]['reasons'] for k in ('indexTrend','wholeMarketTurnover','continuousBreadth','exitPressure')),[])
    if d.get('breadthScope')!='allA' or d.get('exitScope')!='allA':whole.append('selected or unknown breadth/exit pool is not full A-share coverage')
    gate('wholeMarketState',whole)
    return {'targetSession':target_session,'gates':out,'sourceVerified':False,'limits':'conditional metadata checks; no bull/bear or exit-safety certificate'}
