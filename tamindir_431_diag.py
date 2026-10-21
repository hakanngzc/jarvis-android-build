#!/usr/bin/env python3
import html,http.cookiejar,re,urllib.request,urllib.parse
PAGE='https://www.tamindir.com/indir/new-star-soccer-apk/'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36'
jar=http.cookiejar.CookieJar()
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def open_req(url,ref=None,read=True):
 h={'User-Agent':UA,'Accept':'*/*','Accept-Language':'tr-TR,tr;q=0.9,en;q=0.7'}
 if ref:h['Referer']=ref
 req=urllib.request.Request(url,headers=h)
 r=opener.open(req,timeout=90)
 print('HTTP',r.status,'final=',r.geturl(),'ctype=',r.headers.get('Content-Type'),'clen=',r.headers.get('Content-Length'),'disp=',r.headers.get('Content-Disposition'))
 if not read:return r
 b=r.read(); r.close(); print('BODY_BYTES',len(b)); return b,r.geturl()
raw,final=open_req(PAGE)
t=raw.decode('utf-8','replace')
# Select the explicit 4.31 Normal İndirme link, not the primary ad-mediated button.
m=re.search(r'''onclick=["']return\s+downloadAds\(event,\s*["']([^"']*token=[^"']*&v=98774)["']\)''',t,re.I)
if not m:
 # Attribute quote nesting can vary; fall back to the exact route around v=98774.
 m=re.search(r'''(/android/new-star-soccer-apk/indir/\?[^'"<>\s]*v=98774[^'"<>\s]*)''',t,re.I)
if not m: raise SystemExit('normal 4.31 endpoint not found')
path=html.unescape(m.group(1)).replace('\\/','/')
url=urllib.parse.urljoin(final,path)
print('NORMAL_PATH',path)
print('COOKIE_COUNT',len(list(jar)))
r=open_req(url,final,read=False)
ctype=(r.headers.get('Content-Type') or '').lower()
clen=r.headers.get('Content-Length')
if 'text/' not in ctype and 'html' not in ctype:
 print('BINARY_ENDPOINT=TRUE')
 print('FINAL_URL',r.geturl())
 r.close()
 raise SystemExit(0)
# Small interstitial: inspect without downloading a large binary.
b=r.read(1500000); r.close(); print('INTERSTITIAL_BYTES',len(b))
s=b.decode('utf-8','replace')
for needle in ['proceedWithDownload','window.location','location.href','download','token','apk','xapk']:
 print('\nCTX',needle)
 for x in list(re.finditer(re.escape(needle),s,re.I))[:12]:
  print(re.sub(r'\s+',' ',html.unescape(s[max(0,x.start()-1000):x.start()+2200]))[:3200])
for pat in [r'''https?://[^"'<>\s]+''',r'''(?:href|data-url|data-href)\s*=\s*["']([^"']+)["']''']:
 vals=[]
 for mm in re.finditer(pat,s,re.I):
  v=mm.group(1) if mm.lastindex else mm.group(0)
  v=html.unescape(v).replace('\\/','/')
  if re.search(r'apk|xapk|download|indir|cdn|dosya|file',v,re.I) and v not in vals: vals.append(v)
 print('CANDIDATES',vals[:80])
