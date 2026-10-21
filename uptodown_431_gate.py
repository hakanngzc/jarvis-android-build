#!/usr/bin/env python3
import html,re,sys,urllib.parse,urllib.request,http.cookiejar
from pathlib import Path
PAGE='https://www.tamindir.com/indir/new-star-soccer-apk/'
ORIGIN='https://www.tamindir.com'
REPORT=Path(sys.argv[2])
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36'
jar=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def fetch(url,ref=None):
 h={'User-Agent':UA,'Accept':'*/*','Accept-Language':'tr-TR,tr;q=0.9,en;q=0.8'}
 if ref:h['Referer']=ref
 with op.open(urllib.request.Request(url,headers=h),timeout=120) as r:return r.read(),r.geturl(),r.headers,r.status
raw,final,_,_=fetch(PAGE)
text=html.unescape(raw.decode('utf-8','replace')).replace('\\/','/')
urls=re.findall(r'''downloadAds\(event,\s*["']([^"']+)["']\)''',text,re.I)
urls=[u for u in urls if re.search(r'(?:\?|&)v=98774(?:&|$)',u)]
if not urls: raise SystemExit('v=98774 endpoint missing')
endpoint=urllib.parse.urljoin(ORIGIN,urls[0]); print('ENDPOINT',endpoint)
data,f2,h2,s2=fetch(endpoint,final); mid=html.unescape(data.decode('utf-8','replace')).replace('\\/','/')
print('MIDDLE',s2,f2,h2.get('Content-Type'),'bytes=',len(data))
for needle in ('proceedWithDownload','dynamicAdClick','downloadAds','downloadUrl','downloadURL','fileUrl','fileURL','location.href','window.location','redirect','token','98774','.apk','cdn','dosya','indir'):
 print('\n###',needle)
 start=0;n=0
 while n<12:
  p=mid.lower().find(needle.lower(),start)
  if p<0:break
  print('POS',p,'CTX',repr(mid[max(0,p-1200):p+3500]));start=p+len(needle);n+=1
print('\n### SCRIPTS')
for tag in re.findall(r'''<script\b[^>]*>.*?</script>''',mid,re.I|re.S):
 low=tag.lower()
 if any(k in low for k in ('proceedwithdownload','dynamicadclick','download','redirect','location.href','98774')):
  print(repr(tag[:12000]))
print('\n### SRC')
for src in re.findall(r'''<script\b[^>]*\bsrc=["']([^"']+)["']''',mid,re.I):print(urllib.parse.urljoin(f2,html.unescape(src)))
REPORT.write_text('SOURCE_GATE=DIAGNOSTIC\nsource=tamindir-middle-page\n')
print(REPORT.read_text(),end='')
