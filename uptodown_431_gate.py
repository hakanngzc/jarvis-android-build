#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, io, json, re, sys, urllib.request, zipfile
from pathlib import Path
BASE='https://new-star-soccer.en.uptodown.com/android'
VERSION_ID='1129097900'
APP_CODE='18771'
DATA_VERSION='12062304'
EXPECTED='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36'
OUT=Path(sys.argv[1]); REPORT=Path(sys.argv[2])
def fetch(url, ref=None):
 h={'User-Agent':UA,'Accept':'*/*'}
 if ref: h['Referer']=ref
 with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=240) as r:return r.read(),r.geturl(),r.headers,r.status
def digest(b):return hashlib.sha256(b).hexdigest()
def inspect(data,url):
 d=digest(data); print('BINARY',len(data),d,url)
 if data[:2]!=b'PK': return False
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  for n in [x for x in z.namelist() if x.lower().endswith('.apk')]:
   p=z.read(n); h=digest(p); print('APK',n,len(p),h,h==EXPECTED)
   if h==EXPECTED:
    OUT.write_bytes(data); REPORT.write_text(f'SOURCE_GATE=PASS\nsource=uptodown\nurl={url}\nentry={n}\nbase_sha256={h}\nbinary_published=NO\n'); return True
 return False
try:
 page=f'{BASE}/download/{VERSION_ID}'
 raw,final,_,_=fetch(page,BASE+'/versions')
 print('PAGE',final,len(raw))
 files=f'https://new-star-soccer.en.uptodown.com/app/{APP_CODE}/version/{DATA_VERSION}/files'
 blob,ff,_,_=fetch(files,final)
 obj=json.loads(blob.decode('utf-8','replace'))
 content=html.unescape(str(obj.get('content',''))).replace('\\/','/')
 print('FILES_JSON_KEYS',sorted(obj.keys()))
 print('FILES_CONTENT_REPR',repr(content))
 print('ALL_ATTRS')
 for m in re.finditer(r'''([\w:-]+)\s*=\s*["']([^"']+)["']''',content,re.I):
  k,v=m.groups()
  if any(x in k.lower()+v.lower() for x in ('url','href','onclick','download','file','post')): print(k,repr(v))
 print('ALL_URLISH')
 for m in re.finditer(r'''(?:https?://|/)[^"'<>\s]+''',content,re.I): print(repr(m.group(0)))
 for suffix in ('-x',''):
  purl=f'{BASE}/download/{VERSION_ID}{suffix}'
  pr,pf,_,_=fetch(purl,final); text=pr.decode('utf-8','replace')
  print('FILE_PAGE',suffix,pf,len(pr))
  for needle in ('detail-download-button','post-download','data-url','data-file-id','turnstile'):
   pos=text.lower().find(needle)
   print('NEEDLE',needle,'POS',pos)
   if pos>=0: print('CTX',repr(text[max(0,pos-500):pos+1800]))
 REPORT.write_text('SOURCE_GATE=FAIL\nsource=uptodown\nreason=diagnostic-no-binary-yet\nexpected_base_sha256='+EXPECTED+'\n')
 print(REPORT.read_text(),end='')
 raise SystemExit(3)
except Exception as e:
 REPORT.write_text(f'SOURCE_GATE=FAIL\nsource=uptodown\nreason={type(e).__name__}:{e}\nexpected_base_sha256={EXPECTED}\n')
 print(REPORT.read_text(),end=''); raise
