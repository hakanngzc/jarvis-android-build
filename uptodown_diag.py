#!/usr/bin/env python3
import html,re,urllib.request,urllib.parse,json
BASE='https://new-star-soccer.en.uptodown.com/android'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36'
def get(url,ref=None):
 h={'User-Agent':UA,'Accept':'*/*'}
 if ref:h['Referer']=ref
 r=urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=60)
 b=r.read(); print('GET',r.status,r.geturl(),r.headers.get('Content-Type'),len(b)); return b,r.geturl()
raw,u=get(BASE+'/versions')
t=raw.decode('utf-8','replace')
m=re.search(r'<div[^>]*data-version-id=["\']1129097900["\'][^>]*>',t,re.I)
print('VERSION_TAG',m.group(0) if m else 'NONE')
page=BASE+'/download/1129097900'
raw,u=get(page,u); t=raw.decode('utf-8','replace')
for pat in ['detail-download-button','detail-app-name','button variants','post-download','data-file-id']:
 print('\n--',pat,'--')
 for x in re.findall(r'<[^>]*'+re.escape(pat.split()[0])+r'[^>]*>',t,re.I)[:20]: print(html.unescape(x))
for name in ['data-url','data-version','data-code','code','data-file-id']:
 vals=[]
 for mm in re.finditer(r'\b'+name+r'\s*=\s*["\']([^"\']+)["\']',t,re.I):
  v=html.unescape(mm.group(1))
  if v not in vals: vals.append(v)
 print(name,vals[:30])
