import urllib.request
import json
import os

BASE_URL = 'http://127.0.0.1:8000/api/v1'

def login():
    data = json.dumps({'email': 'test6@test.com', 'password': 'Password123!'}).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}/auth/login', data=data, headers={'Content-Type': 'application/json'})
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read())['access_token']
    except Exception as e:
        print("Login failed:", e)
        return None

def fetch_paper(token, paper_id):
    req = urllib.request.Request(f'{BASE_URL}/question-papers/{paper_id}', headers={'Authorization': f'Bearer {token}'})
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read())
    except Exception as e:
        print("Fetch failed:", e)
        return None

def publish_paper(token, paper_id):
    req = urllib.request.Request(f'{BASE_URL}/question-papers/{paper_id}/publish', data=b'', headers={'Authorization': f'Bearer {token}'})
    try:
        res = urllib.request.urlopen(req)
        print(f"Publish {paper_id} Success")
    except Exception as e:
        print(f"Publish {paper_id} Failed:", e.read().decode() if hasattr(e, 'read') else str(e))

def lock_paper(token, paper_id):
    req = urllib.request.Request(f'{BASE_URL}/question-papers/{paper_id}/lock', data=b'', headers={'Authorization': f'Bearer {token}'})
    try:
        res = urllib.request.urlopen(req)
        print(f"Lock {paper_id} Success")
    except Exception as e:
        print(f"Lock {paper_id} Failed:", e.read().decode() if hasattr(e, 'read') else str(e))

def archive_paper(token, paper_id):
    req = urllib.request.Request(f'{BASE_URL}/question-papers/{paper_id}/archive', data=b'', headers={'Authorization': f'Bearer {token}'})
    try:
        res = urllib.request.urlopen(req)
        print(f"Archive {paper_id} Success")
    except Exception as e:
        print(f"Archive {paper_id} Failed:", e.read().decode() if hasattr(e, 'read') else str(e))

def update_paper(token, paper_id):
    data = json.dumps({'title': 'Attempted Edit'}).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}/question-papers/{paper_id}', data=data, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}', 'Method': 'PUT'}, method='PUT')
    try:
        res = urllib.request.urlopen(req)
        print(f"Update {paper_id} Success")
    except Exception as e:
        print(f"Update {paper_id} Failed:", e.read().decode() if hasattr(e, 'read') else str(e))

def create_structured_paper(token):
    data = json.dumps({'title': 'Test structured paper', 'course_name': 'Test', 'description': ''}).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}/question-paper-builder/', data=data, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read())['id']
    except Exception as e:
        print("Create failed:", e)
        if hasattr(e, 'read'):
            print(e.read().decode())
        return None

def create_file_paper(token):
    import urllib.parse
    
    # Simple form data payload
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"title\"\r\n\r\n"
        f"Test file paper\r\n"
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"course_name\"\r\n\r\n"
        f"Test Course\r\n"
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"test.txt\"\r\n"
        f"Content-Type: text/plain\r\n\r\n"
        f"test content\r\n"
        f"--{boundary}--\r\n"
    ).encode('utf-8')
    
    req = urllib.request.Request(
        f'{BASE_URL}/question-papers/', 
        data=body, 
        headers={
            'Content-Type': f'multipart/form-data; boundary={boundary}', 
            'Authorization': f'Bearer {token}'
        }
    )
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read())['id']
    except Exception as e:
        print("Create failed:", e)
        if hasattr(e, 'read'):
            print(e.read().decode())
        return None

if __name__ == "__main__":
    token = login()
    if token:
        print("Logged in")
        paper_id = create_structured_paper(token)
        if paper_id:
            print(f"Created Paper ID: {paper_id}")
            
            # 1. Update DRAFT
            update_paper(token, paper_id)
            
            # 2. Lock DRAFT (Should fail)
            lock_paper(token, paper_id)
            
            # 3. Publish DRAFT
            publish_paper(token, paper_id)
            
            # 4. Update READY (Should succeed)
            update_paper(token, paper_id)
            
            # 5. Archive READY (Should fail)
            archive_paper(token, paper_id)
            
            # 6. Lock READY
            lock_paper(token, paper_id)
            
            # 7. Update LOCKED (Should fail)
            update_paper(token, paper_id)
            
            # 8. Archive LOCKED
            archive_paper(token, paper_id)
            
            # 9. Update ARCHIVED (Should fail)
            update_paper(token, paper_id)
