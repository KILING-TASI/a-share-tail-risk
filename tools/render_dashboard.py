"""Render a dated local snapshot without publishing the input dataset."""
import argparse,json,re
from pathlib import Path
from market_contract import assess
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--session',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    p=Path(a.output)
    if p.exists():raise FileExistsError('refusing to overwrite a frozen snapshot')
    data=json.loads(Path(a.input).read_text(encoding='utf-8'));data['assessment']=assess(data,a.session)
    encoded=json.dumps(data,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    s=(ROOT/'dashboard-template.html').read_text(encoding='utf-8');s=re.sub(r'(<script id="market-data" type="application/json">)[\s\S]*?(</script>)',lambda m:m[1]+encoded+m[2],s,count=1);s=s.replace('__APP__',(ROOT/'tools/market-app.js').read_text(encoding='utf-8'));p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8');print(str(p))
if __name__=='__main__':main()
