import urllib.request
import json
import sys

def register(email):
    data = json.dumps({
        'email': email, 
        'password': 'Password123!', 
        'full_name': 'Test User', 
        'confirm_password': 'Password123!'
    }).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/register', data=data, headers={'Content-Type': 'application/json'})
    try:
        res = urllib.request.urlopen(req)
        print(res.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error {e.code}: {e.read().decode()}")

if __name__ == "__main__":
    register(sys.argv[1])
