#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sys, urllib.parse, urllib.request
from pathlib import Path
PKG='com.newstargames.newstarsoccer'; VCODE=137; VNAME='4.31'
EXPECTED='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'
OUT=Path(sys.argv[1]); REPORT=Path(sys.argv[2])
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36'
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'*/*'})
 with urllib.request.urlopen(req,timeout=240) as r:return r.read(),r.geturl(),r.headers,r.status
def sha(b):return hashlib.sha256(b).hexdigest()
def walk(o):
 if isinstance(o,dict):
  if 'vercode' in o and ('path' in o or 'path_alt' in o): yield o
  for v in o.values(): yield from walk(v)
 elif isinstance(o,list):
  for v in o: yield from walk(v)
try:
 candidates=[]
 urls=[]
 for host in ('ws75.aptoide.com','ws2.aptoide.com'):
  urls += [
   f'https://{host}/api/7/app/get/package_name={PKG}',
   f'https://{host}/api/7/app/get?package_name={urllib.parse.quote(PKG)}',
  ]
 for url in urls:
  try:
   raw,final,h,s=fetch(url); print('API',s,final,h.get('Content-Type'),'bytes=',len(raw))
   obj=json.loads(raw.decode('utf-8','replace'))
  except Exception as e:
   print('API_ERROR',url,type(e).__name__,e); continue
  print('API_STATUS',obj.get('info',{}).get('status'))
  for f in walk(obj):
   try: code=int(f.get('vercode'))
   except Exception: continue
   if code==VCODE or str(f.get('vername',''))==VNAME:
    row={k:f.get(k) for k in ('vername','vercode','md5sum','filesize','path','path_alt')}
    print('VERSION_CANDIDATE',json.dumps(row,sort_keys=True))
    candidates.append(f)
 if not candidates: raise RuntimeError('Aptoide API returned no 4.31/versionCode 137 file candidate')
 seen=set()
 for f in candidates:
  for key in ('path','path_alt'):
   url=f.get(key)
   if not url or url in seen: continue
   seen.add(url)
   try: data,final,h,s=fetch(url)
   except Exception as e: print('DOWNLOAD_ERROR',key,type(e).__name__,e); continue
   d=sha(data); print('DOWNLOAD',key,s,final,h.get('Content-Type'),'bytes=',len(data),'sha256=',d,'EXPECTED=',d==EXPECTED)
   if d==EXPECTED:
    OUT.write_bytes(data)
    REPORT.write_text('SOURCE_GATE=PASS\nsource=aptoide-api\npackage='+PKG+'\nversion_name=4.31\nversion_code=137\nurl='+final+'\nbase_sha256='+d+'\nbinary_published=NO\n')
    print(REPORT.read_text(),end=''); raise SystemExit(0)
 raise RuntimeError('Aptoide 4.31 candidates downloaded but none matched expected base APK SHA-256')
except Exception as e:
 REPORT.write_text('SOURCE_GATE=FAIL\nsource=aptoide-api\nreason='+type(e).__name__+':'+str(e)+'\nexpected_base_sha256='+EXPECTED+'\n')
 print(REPORT.read_text(),end=''); raise SystemExit(3)
