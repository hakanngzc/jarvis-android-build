#!/usr/bin/env python3
import hashlib
import html
import re
import urllib.parse
import urllib.request

EXPECTED_GIT_BLOB_SHA1 = "0d7a2ae9b0b6e77155a77c0770be022771782bd0"
PAGE = "https://www.tamindir.com/indir/new-star-soccer-apk/"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36"

def fetch(url, referer=None):
    headers={"User-Agent":UA,"Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8"}
    if referer: headers["Referer"] = referer
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=240) as r:
        return r.read(),r.geturl(),r.headers,r.status

raw,final,headers,status=fetch(PAGE)
text=raw.decode("utf-8","replace")
print("page_status=",status)
# Find the exact 4.31 Normal Indirme path from the live page, do not hard-code stale token.
pat=r'''downloadAds\(event,\s*['"]([^'"]*?/android/new-star-soccer-apk/indir/\?[^'"]*?v=98774[^'"]*)['"]\)'''
m=re.search(pat,text,re.I)
if not m:
    raise SystemExit("4.31 Tamindir normal download URL not found")
path=html.unescape(m.group(1))
url=urllib.parse.urljoin(PAGE,path)
print("normal_download_url=",url)

try:
    data,download_final,h,download_status=fetch(url,PAGE)
except Exception as e:
    raise SystemExit("download_failed="+repr(e))
print("download_status=",download_status)
print("download_final_url=",download_final)
print("content_type=",h.get("Content-Type"))
print("content_disposition=",h.get("Content-Disposition"))
print("bytes=",len(data))
print("head=",data[:16].hex())
print("sha256=",hashlib.sha256(data).hexdigest())
git_blob=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
print("git_blob_sha1=",git_blob)
print("expected_git_blob_sha1=",EXPECTED_GIT_BLOB_SHA1)
print("exact_private_base_match=",git_blob==EXPECTED_GIT_BLOB_SHA1)
if data[:2]==b"PK":
    open("/tmp/nss431-download.bin","wb").write(data)
    print("zip_like=TRUE")
else:
    print("zip_like=FALSE")
    print(data[:3000].decode("utf-8","replace"))
