#!/usr/bin/env python3
import html,re,urllib.request,urllib.parse
PAGE='https://www.tamindir.com/indir/new-star-soccer-apk/'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36'
def get(url,ref=None):
 h={'User-Agent':UA,'Accept':'*/*','Accept-Language':'tr-TR,tr;q=0.9,en;q=0.7'}
 if ref:h['Referer']=ref
 req=urllib.request.Request(url,headers=h)
 with urllib.request.urlopen(req,timeout=60) as r:
  b=r.read(); print('GET',r.status,r.geturl(),r.headers.get('Content-Type'),len(b)); return b,r.geturl()
raw,final=get(PAGE)
t=raw.decode('utf-8','replace')
for needle in ['4.31','Normal İndirme','Normal Indirme','75.70','download','indir']:
 print('\nHTML_CONTEXT',needle)
 for m in list(re.finditer(re.escape(needle),t,re.I))[:10]:
  print(re.sub(r'\s+',' ',html.unescape(t[max(0,m.start()-1400):m.start()+3000]))[:4400])
attrs=['href','data-url','data-href','data-download','data-link','data-file','data-id','data-version','onclick']
for name in attrs:
 vals=[]
 for m in re.finditer(r'\b'+re.escape(name)+r'\s*=\s*["\']([^"\']+)["\']',t,re.I):
  v=html.unescape(m.group(1)).replace('\\/','/')
  if re.search(r'new.star|4\.31|download|indir|apk|xapk|file|cdn',v,re.I) and v not in vals: vals.append(v)
 print('\nATTR',name,vals[:80])
scripts=[]
for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']',t,re.I):
 u=urllib.parse.urljoin(final,html.unescape(m.group(1)))
 if u not in scripts:scripts.append(u)
print('\nSCRIPTS',scripts)
needles=['download','indir','normal-download','normalDownload','fileUrl','downloadUrl','download-url','product-download']
for u in scripts[:30]:
 try:b,fu=get(u,final)
 except Exception as e: print('JS_ERR',u,type(e).__name__,e); continue
 js=b.decode('utf-8','replace')
 hits=[n for n in needles if re.search(re.escape(n),js,re.I)]
 if not hits:continue
 print('\nJS_MATCH',fu,hits)
 for n in hits:
  for m in list(re.finditer(re.escape(n),js,re.I))[:8]:
   print('CTX',n,re.sub(r'\s+',' ',js[max(0,m.start()-1200):m.start()+2600])[:3800])
