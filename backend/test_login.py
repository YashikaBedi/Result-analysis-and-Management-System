import requests

try:
    s = requests.Session()
    r = s.get('http://127.0.0.1:5000/auth/login')
    csrf_token = r.text.split('name="csrf_token" type="hidden" value="')[1].split('"')[0]
    
    data = {'username': 'admin', 'password': 'admin123', 'csrf_token': csrf_token, 'submit': 'Login'}
    r2 = s.post('http://127.0.0.1:5000/auth/login', data=data, allow_redirects=False)
    print(f"POST /auth/login -> {r2.status_code} {r2.headers.get('Location')}")
    
    # Follow chain
    next_url = 'http://127.0.0.1:5000' + r2.headers.get('Location')
    for i in range(5):
        r_current = s.get(next_url, allow_redirects=False)
        print(f"GET {next_url} -> {r_current.status_code} {r_current.headers.get('Location')}")
        if r_current.status_code in (301, 302, 303):
            loc = r_current.headers.get('Location')
            if not loc.startswith('http'):
                loc = 'http://127.0.0.1:5000' + loc
            next_url = loc
        else:
            print("Finished redirect chain.")
            break
            
except Exception as e:
    print("Error:", e)
