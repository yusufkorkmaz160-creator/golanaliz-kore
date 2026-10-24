#!/usr/bin/env python3
"""Fetch K League fixtures from candidate public CSV/JSON downloads.
Never publishes fabricated matches; preserves last good data on failure.
"""
import csv, io, json, os, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'korea_fixtures.json'
SOURCES={
 'K League 1':'https://futpythontrader.com.br/api/download/south-korea/k-league-1/2026',
 'K League 2':'https://futpythontrader.com.br/api/download/south-korea/k-league-2/2026',
}

def first(row,*keys):
 d={str(k).strip().lower():v for k,v in row.items()}
 return next((str(d[k]).strip() for k in keys if d.get(k) is not None and str(d[k]).strip()),'')

def parse_date(s):
 s=s.strip()
 for fmt in ('%Y-%m-%d','%d/%m/%Y','%Y/%m/%d','%d-%m-%Y','%Y-%m-%d %H:%M:%S','%d/%m/%Y %H:%M'):
  try:return datetime.strptime(s,fmt).strftime('%Y-%m-%d')
  except ValueError:pass
 m=re.search(r'20\d\d[-/]\d\d[-/]\d\d',s)
 return m.group().replace('/','-') if m else ''

def records(payload):
 if isinstance(payload,list):return payload
 if isinstance(payload,dict):
  for key in ('matches','fixtures','data','events','results','list'):
   if isinstance(payload.get(key),list):return payload[key]
   if isinstance(payload.get(key),dict):
    nested=records(payload[key]);
    if nested:return nested
 return []

def download(url):
 req=urllib.request.Request(url,headers={'User-Agent':'GolAnaliz-Kore/1.0','Accept':'application/json,text/csv,*/*'})
 with urllib.request.urlopen(req,timeout=25) as r:
  content=r.read(8_000_000).decode('utf-8-sig'); ctype=r.headers.get('Content-Type','')
 if 'json' in ctype or content.lstrip().startswith(('{','[')):
  return records(json.loads(content))
 if '<html' in content[:300].lower():raise ValueError('HTML page returned, not match data')
 return list(csv.DictReader(io.StringIO(content)))

def main():
 allrows=[]; failures=[]
 for league,url in SOURCES.items():
  try:
   rows=download(url); valid=[]
   for row in rows:
    if not isinstance(row,dict):continue
    date=parse_date(first(row,'date','match_date','game_date','data','datetime','fixture_date'))
    home=first(row,'home','home_team','hometeam','home_team_name','mandante','time_casa')
    away=first(row,'away','away_team','awayteam','away_team_name','visitante','time_fora')
    if date.startswith('2026-') and home and away and home!=away:
     valid.append({'date':date,'home':home,'away':away,'league':league})
   if not valid:raise ValueError(f'{len(rows)} rows but no recognized 2026 fixtures; inspect schema')
   allrows+=valid
   print(f'{league}: {len(valid)} fixtures')
  except Exception as e:
   failures.append(f'{league}: {e}')
 if failures:
  for msg in failures:print('ERROR',msg)
  raise SystemExit('One or more sources failed. Existing JSON unchanged.')
 uniq={(r['league'],r['date'],r['home'],r['away']):r for r in allrows}
 payload={'updated_at':datetime.now(timezone.utc).isoformat(),'season':2026,'source':'futpythontrader public download (unverified availability)','matches':sorted(uniq.values(),key=lambda r:(r['date'],r['league'],r['home']))}
 tmp=OUT.with_suffix('.json.tmp');tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(tmp,OUT)
 print(f'Published {len(uniq)} fixtures')
if __name__=='__main__':main()
