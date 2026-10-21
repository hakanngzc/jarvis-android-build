#!/usr/bin/env python3
import html,re,urllib.request,urllib.parse
BASE='https://new-star-soccer.en.uptodown.com/android'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36'
def get(url,ref=None):
 h={'User-Agent':UA,'Accept':'*/*'}
 if ref:h['Referer']=ref
 r=urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=60)
 b=r.read(); print('GET',r.status,r.geturl(),r.headers.get('Content-Type'),len(b)); return b,r.geturl()
raw,page=get(BASE+'/download/1129097900-x')
t=raw.decode('utf-8','replace')
print('BUTTON', re.findall(r'<button id="detail-download-button"[^>]*>',t,re.I)[:1])
patterns=['post-download','detail-download-button','data-file-id','download-version','downloadApp','only-xapk']
for p in patterns:
 print('\nHTML_CONTEXT',p)
 for m in list(re.finditer(re.escape(p),t,re.I))[:8]:
  print(re.sub(r'\s+',' ',t[max(0,m.start()-600):m.start()+1400])[:2000])
scripts=[]
for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']',t,re.I):
 u=urllib.parse.urljoin(page,html.unescape(m.group(1)))
 if u not in scripts: scripts.append(u)
print('SCRIPTS',scripts)
for u in scripts[:25]:
 try: b,fu=get(u,page)
 except Exception as e: print('JS_ERR',u,type(e).__name__,e); continue
 js=b.decode('utf-8','replace')
 hits=[]
 for p in patterns:
  if re.search(re.escape(p),js,re.I): hits.append(p)
 if not hits: continue
 print('\nJS_MATCH',fu,hits)
 for p in hits:
  for m in list(re.finditer(re.escape(p),js,re.I))[:6]:
   print('CTX',p,re.sub(r'\s+',' ',js[max(0,m.start()-900):m.start()+1800])[:2700])
