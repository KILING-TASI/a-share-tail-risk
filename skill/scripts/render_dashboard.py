"""Render a dated local snapshot without publishing the input dataset."""
import sys,argparse,json,re
from pathlib import Path
from market_gates import assess
from research_summary import summarize
ROOT=Path(__file__).resolve().parents[1]
def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--session',required=True);ap.add_argument('--output',required=True);ap.add_argument('--assets');ap.add_argument('--research');ap.add_argument('--previous-research');ap.add_argument('--context');a=ap.parse_args()
    p=Path(a.output)
    if p.exists():raise FileExistsError('refusing to overwrite a frozen snapshot')
    data=json.loads(Path(a.input).read_text(encoding='utf-8'));data['assessment']=assess(data,a.session)
    encoded=json.dumps(data,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    s=(ROOT/'assets/market-dashboard.html').read_text(encoding='utf-8');s=re.sub(r'(<script id="market-data" type="application/json">)[\s\S]*?(</script>)',lambda m:m[1]+encoded+m[2],s,count=1);assets=json.loads(Path(a.assets).read_text(encoding='utf-8')) if a.assets else {}
    ae=json.dumps(assets,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    s=s.replace('__ASSET_DATA__',ae)
    research=json.loads(Path(a.research).read_text(encoding='utf-8')) if a.research else summarize(assets,data,json.loads(Path(a.previous_research).read_text(encoding='utf-8')) if a.previous_research else None)
    if a.context:research['context']=json.loads(Path(a.context).read_text(encoding='utf-8'))
    s=s.replace('__RESEARCH_DATA__',json.dumps(research,ensure_ascii=False,allow_nan=False).replace('<','\\u003c'))
    s=s.replace('__ADVANCED_APP__',(ROOT/'assets/advanced-app.js').read_text(encoding='utf-8'))
    s=s.replace('__LAB_APP__',(ROOT/'assets/risk-lab.js').read_text(encoding='utf-8'))
    s=s.replace('__RESEARCH_APP__',(ROOT/'assets/research-app.js').read_text(encoding='utf-8'))
    s=s.replace('__APP__',(ROOT/'assets/market-app.js').read_text(encoding='utf-8'));p.parent.mkdir(parents=True,exist_ok=True);p.open('x',encoding='utf-8').write(s);print(str(p))
if __name__=='__main__':main()
