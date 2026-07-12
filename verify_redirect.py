import urllib.request

req = urllib.request.Request('http://127.0.0.1:3000/', method='GET')
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print(r.status)
        print(r.read().decode()[:200])
except Exception as e:
    print(type(e).__name__)
    print(e)
