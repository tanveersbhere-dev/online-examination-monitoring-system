import urllib.request
import json
import urllib.error
from datetime import datetime, timedelta, timezone

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

def test_exam_workflow():
    import urllib.parse
    token = login()
    if not token:
        return
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}

    # 1. Create Question Paper (Structured)
    print("1. Creating Assessment...")
    data = json.dumps({'title': 'Workflow Assessment', 'course_name': 'Test', 'description': ''}).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}/question-paper-builder/', data=data, headers=headers)
    paper_id = json.loads(urllib.request.urlopen(req).read())['id']
    
    # Publish Assessment to READY
    req = urllib.request.Request(f'{BASE_URL}/question-papers/{paper_id}/publish', data=b'', headers=headers)
    urllib.request.urlopen(req)
    print(f"   Created and published Assessment ID: {paper_id}")

    # 2. Create Exam
    print("\n2. Creating Exam (Draft)...")
    exam_data = {
        'title': 'Final Exam 2026',
        'course_name': 'CS101',
        'duration_minutes': 120,
        'question_paper_id': paper_id,
        'timezone': 'UTC'
    }
    req = urllib.request.Request(f'{BASE_URL}/workspace/exams/', data=json.dumps(exam_data).encode('utf-8'), headers=headers)
    try:
        exam = json.loads(urllib.request.urlopen(req).read())
        exam_id = exam['id']
        print(f"   Created Exam ID: {exam_id}")
    except urllib.error.HTTPError as e:
        print("   Failed to create exam:", e.read().decode())
        return

    # 3. Assign Students
    print("\n3. Assigning Students...")
    # Get students first
    req = urllib.request.Request(f'{BASE_URL}/workspace/students', headers=headers)
    students = json.loads(urllib.request.urlopen(req).read())
    student_ids = [s['id'] for s in students['items']] if isinstance(students, dict) and 'items' in students else [s['id'] for s in students]
    if not student_ids:
        print("   No students found to assign.")
    else:
        assign_data = {'student_ids': student_ids[:2]}
        req = urllib.request.Request(f'{BASE_URL}/workspace/exams/{exam_id}/students', data=json.dumps(assign_data).encode('utf-8'), headers=headers)
        res = urllib.request.urlopen(req)
        print("   ", json.loads(res.read())['message'])

    # 4. Assign Supervisors
    print("\n4. Assigning Supervisors...")
    # There's no supervisor API to fetch them, so we will try a dummy ID.
    supervisor_data = {'supervisor_ids': [1]} # Using examiner's own ID as a test
    req = urllib.request.Request(f'{BASE_URL}/workspace/exams/{exam_id}/supervisors', data=json.dumps(supervisor_data).encode('utf-8'), headers=headers)
    res = urllib.request.urlopen(req)
    print("   ", json.loads(res.read())['message'])

    # 5. Configure Schedule
    print("\n5. Configuring Schedule...")
    now = datetime.now(timezone.utc)
    start_time = (now + timedelta(days=1)).isoformat()
    end_time = (now + timedelta(days=1, hours=2)).isoformat()
    update_data = {
        'scheduled_start': start_time,
        'scheduled_end': end_time,
        'question_paper_id': paper_id
    }
    req = urllib.request.Request(f'{BASE_URL}/workspace/exams/{exam_id}', data=json.dumps(update_data).encode('utf-8'), headers=headers, method='PUT')
    urllib.request.urlopen(req)
    print("   Schedule updated successfully.")

    # 6. Publish Exam
    print("\n6. Publishing Exam...")
    req = urllib.request.Request(f'{BASE_URL}/workspace/exams/{exam_id}/publish', data=b'', headers=headers)
    try:
        res = urllib.request.urlopen(req)
        print("   Exam Published Successfully! Status:", json.loads(res.read())['status'])
    except urllib.error.HTTPError as e:
        print("   Failed to publish exam:", e.read().decode())

if __name__ == '__main__':
    test_exam_workflow()
