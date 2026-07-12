import urllib.request

req = urllib.request.Request('http://127.0.0.1:3000/logout')
with urllib.request.urlopen(req, timeout=10) as r:
    print(r.status)
    print(r.geturl())
