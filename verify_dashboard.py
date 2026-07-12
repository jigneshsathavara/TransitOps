import urllib.request
import http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
req = urllib.request.Request('http://127.0.0.1:3000/dashboard.html')
try:
    with opener.open(req, timeout=10) as r:
        print('status', r.status)
        print(r.read().decode()[:200])
except Exception as e:
    print(type(e).__name__)
    print(e)
