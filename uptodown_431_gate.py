#!/usr/bin/env python3
import html,re,sys,urllib.request
from pathlib import Path
URL='https://www.tamindir.com/indir/new-star-soccer-apk/'
REPORT=Path(sys.argv[2])
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36'
req=urllib.request.Request(URL,headers={'User-Agent':UA,'Accept':'text/html,*/*','Accept-Language':'tr-TR,tr;q=0.9,en;q=0.8'})
try:
 with urllib.request.urlopen(req,timeout=120) as r: raw=r.read(); final=r.geturl(); print('PAGE',r.status,final,r.headers.get('Content-Type'),'bytes=',len(raw))
 text=html.unescape(raw.decode('utf-8','replace')).replace('\\/','/')
 for needle in ('4.31','75.70','Normal İndirme','Normal Indirme','app-version-display','download','indir'):
  print('\n### NEEDLE',needle)
  start=0; count=0
  while count<8:
   p=text.lower().find(needle.lower(),start)
   if p<0: break
   print('POS',p,'CTX',repr(text[max(0,p-900):p+2400])); start=p+len(needle); count+=1
 print('\n### URLS')
 seen=set()
 for m in re.finditer(r'''https?://[^"'<>\s]+''',text,re.I):
  u=m.group(0).rstrip('),;')
  if any(k in u.lower() for k in ('apk','download','indir','tamindir','new-star','newstar')) and u not in seen:
   seen.add(u); print(u)
 print('\n### DOWNLOADISH_TAGS')
 for tag in re.findall(r'<[^>]+>',text,re.S):
  low=tag.lower()
  if any(k in low for k in ('download','indir','4.31','75.70','data-version','data-file','data-url')):
   print(re.sub(r'\s+',' ',tag)[:2400])
 REPORT.write_text('SOURCE_GATE=FAIL\nsource=tamindir\nreason=diagnostic\n')
except Exception as e:
 REPORT.write_text('SOURCE_GATE=FAIL\nsource=tamindir\nreason='+type(e).__name__+':'+str(e)+'\n'); print(REPORT.read_text()); raise
