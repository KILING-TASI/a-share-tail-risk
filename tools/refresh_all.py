"""One command for local market + selected assets + report. New directory only."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--session',required=True);ap.add_argument('--output',required=True);ap.add_argument('--manifest',default=str(ROOT/'skill/examples/asset-manifest.json'));ap.add_argument('--previous-assets');ap.add_argument('--observations');ap.add_argument('--previous-research');ap.add_argument('--context-manifest',default=str(ROOT/'skill/examples/context-manifest.json'));a=ap.parse_args();out=Path(a.output)
 if out.exists():ap.exit(2,'Use a new version directory; frozen results are not overwritten.\n')
 out.mkdir(parents=True)
 def run(args):subprocess.run([sys.executable]+[str(x) for x in args],check=True)
 market=out/'market';run([ROOT/'tools/update_market.py','--input',ROOT/'examples/official-statistics-20261014.json','--session',a.session,'--output',market]);assets=out/'assets.json';args=[ROOT/'skill/scripts/collect_assets.py','--manifest',a.manifest,'--session',a.session,'--output',assets]
 if a.previous_assets:args+=['--previous',a.previous_assets]
 run(args)
 context=out/'context.json';run([ROOT/'skill/scripts/collect_context.py','--manifest',a.context_manifest,'--session',a.session,'--output',context])
 data=json.loads((market/'market-data.json').read_text(encoding='utf-8'));quotes=json.loads(assets.read_text(encoding='utf-8'))
 csi=next((r for r in quotes['records'] if r['id']=='sh000300' and r['status']=='available'),None)
 if csi:
  data['csi300']=[{'date':x['date'],'close':x['value']} for x in csi.get('history',[])];data['sources'].append({'name':'腾讯沪深300历史价格版本','url':csi['historySourceUrl']})
 if a.observations:
  obs=json.loads(Path(a.observations).read_text(encoding='utf-8'))
  if obs['asOf']!=a.session:raise ValueError('observation date mismatch')
  for k in ('expectedSessions','breadthHistory','breadth','exitPressure','exitHistory','breadthScope','exitScope','groupBasis'):data[k]=obs.get(k)
 data['priorSnapshotAsOf']=data.get('asOf');data['asOf']=a.session;data['asOfMeaning']='requested report cutoff; individual observation dates remain authoritative'
 combined=out/'combined-market.json';combined.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 from sys import path
 path.insert(0,str(ROOT/'skill/scripts'))
 from research_summary import summarize
 previous=json.loads(Path(a.previous_research).read_text(encoding='utf-8')) if a.previous_research else None
 (out/'research.json').write_text(json.dumps(summarize(quotes,data,previous),ensure_ascii=False,allow_nan=False,indent=2),encoding='utf-8')
 run([ROOT/'tools/render_dashboard.py','--input',combined,'--session',a.session,'--assets',assets,'--context',context,'--research',out/'research.json','--output',out/'dashboard.html']);print(out/'dashboard.html')
if __name__=='__main__':main()
