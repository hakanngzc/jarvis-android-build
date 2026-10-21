#!/usr/bin/env python3
import html,http.cookiejar,re,urllib.request,urllib.parse
PAGE='https://www.tamindir.com/indir/new-star-soccer-apk/'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36'
jar=http.cookiejar.CookieJar(); opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def get(url,ref=None):
 h={'User-Agent':UA,'Accept':'*/*','Accept-Language':'tr-TR,tr;q=0.9,en;q=0.7'}
 if ref:h['Referer']=ref
 with opener.open(urllib.request.Request(url,headers=h),timeout=90) as r:
  b=r.read(); print('HTTP',r.status,r.geturl(),r.headers.get('Content-Type'),len(b)); return b,r.geturl()
raw,home=get(PAGE); text=raw.decode('utf-8','replace')
m=re.search(r'''(/android/new-star-soccer-apk/indir/\?[^'"<>\s]*v=98774[^'"<>\s]*)''',text,re.I)
if not m: raise SystemExit('normal endpoint missing')
url=urllib.parse.urljoin(home,html.unescape(m.group(1)))
b,final=get(url,home); s=b.decode('utf-8','replace')
print('FINAL',final)
for pat,label in [
 (r'<meta[^>]+http-equiv=["\']refresh["\'][^>]*>','META_REFRESH'),
 (r'<iframe\b[^>]*>','IFRAME'),
 (r'<form\b[^>]*>','FORM'),
 (r'<script\b[^>]*src=["\'][^"\']+["\'][^>]*>','SCRIPT_SRC'),
 (r'<a\b[^>]+(?:download|indir|apk|xapk)[^>]*>','DOWNLOAD_ANCHOR')]:
 print('\n'+label)
 for x in re.findall(pat,s,re.I)[:50]: print(html.unescape(x))
print('\nINLINE_REDIRECT_SCRIPTS')
for block in re.findall(r'<script\b[^>]*>(.*?)</script>',s,re.I|re.S):
 if re.search(r'setTimeout|location|window\.open|iframe|\.apk|\.xapk|98774|token=',block,re.I):
  print('---',re.sub(r'\s+',' ',html.unescape(block))[:10000])
print('\nALL_SUSPECT_URLS')
vals=[]
for mm in re.finditer(r'''(?:https?:)?//[^"'<>\s]+|/[A-Za-z0-9_./?=&%-]+''',s):
 v=html.unescape(mm.group(0)).replace('\\/','/')
 if re.search(r'apk|xapk|download|indir|cdn|dosya|file|98774|token=',v,re.I) and v not in vals: vals.append(v)
for v in vals[:150]: print(v)
