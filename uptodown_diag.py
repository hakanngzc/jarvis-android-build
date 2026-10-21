#!/usr/bin/env python3
import html,re,urllib.request,json
BASE='https://new-star-soccer.en.uptodown.com/android'
ROOT='https://new-star-soccer.en.uptodown.com'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36'
def get(url,ref=None):
 h={'User-Agent':UA,'Accept':'*/*'}
 if ref:h['Referer']=ref
 r=urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=60)
 b=r.read(); print('GET',r.status,r.geturl(),r.headers.get('Content-Type'),len(b)); return b,r.geturl()
raw,u=get(BASE+'/download/1129097900')
t=raw.decode('utf-8','replace')
print('MAIN', re.findall(r'<button id="detail-download-button"[^>]*>',t,re.I)[:1])
print('APP_CODE', re.findall(r'id="detail-app-name"[^>]*data-code="([^"]+)"',t,re.I))
print('DATA_VERSION', re.findall(r'class="button variants"[^>]*data-version="([^"]+)"',t,re.I))
files_url=ROOT+'/app/18771/version/12062304/files'
b,u2=get(files_url,u)
obj=json.loads(b.decode('utf-8','replace'))
content=html.unescape(str(obj.get('content','')))
print('FILES_CONTENT', re.sub(r'\s+',' ',content)[:12000])
ids=[]
for m in re.finditer(r'data-file-id\s*=\s*["\']([^"\']+)["\']',content,re.I):
 v=m.group(1)
 if v not in ids: ids.append(v)
print('FILE_IDS',ids)
for fid in ids[:12]:
 for suffix in ('-x',''):
  url=f'{BASE}/download/{fid}{suffix}'
  try:
   rb,fu=get(url,u)
  except Exception as e:
   print('ERR',url,type(e).__name__,e); continue
  tt=rb.decode('utf-8','replace')
  tags=re.findall(r'<button id="detail-download-button"[^>]*>',tt,re.I)
  print('PAGE',fid,suffix,'BUTTON',tags[:1])
  vals=re.findall(r'\bdata-url\s*=\s*["\']([^"\']+)["\']',tt,re.I)
  print('DATA_URLS',vals[:10])
