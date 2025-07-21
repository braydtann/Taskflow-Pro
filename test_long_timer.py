#!/usr/bin/env python3
"""
Test Timer with Longer Duration
Test to verify actual_duration works correctly with longer timer sessions
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
import time
import random
import string

# Configuration
BACKEND_URL = "https://5dc9bda8-f77f-4ebb-a8cf-c1393001bfb1.preview.emergentagent.com/api"
TIMEOUT = 30

def generate_test_user_data():
    """Generate realistic test user data"""
    random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return {
        "email": f"long.timer{random_id}@techcorp.com",
        "username": f"long_timer{random_id}",
        "full_name": f"Long Timer User",
        "password": "SecurePass123!"
    }

def test_longer_timer_duration():
    """Test timer with longer duration to verify actual_duration calculation"""
    session = requests.Session()
    session.timeout = TIMEOUT
    
    print("🔍 Testing Timer with Longer Duration")
    print("=" * 50)
    
    # Register user
    user_data = generate_test_user_data()
    response = session.post(f"{BACKEND_URL}/auth/register", json=user_data)
    if response.status_code != 200:
        print(f"❌ User registration failed: {response.status_code}")
        return
    
    token_data = response.json()
    user_info = token_data['user']
    access_token = token_data['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print(f"✅ User registered: {user_info['username']}")
    
    # Create project
    project_data = {
        "name": "Long Timer Project",
        "description": "Project for testing longer timer duration",
        "collaborators": []
    }
    
    response = session.post(f"{BACKEND_URL}/projects", json=project_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ Project creation failed: {response.status_code}")
        return
    
    project = response.json()
    print(f"✅ Project created: {project['name']}")
    
    # Create task
    task_data = {
        "title": "Long Timer Task",
        "description": "Task for testing longer timer duration",
        "priority": "high",
        "project_id": project['id'],
        "estimated_duration": 120,  # 2 hours
        "assigned_users": [],
        "collaborators": [],
        "tags": ["timer", "test"]
    }
    
    response = session.post(f"{BACKEND_URL}/tasks", json=task_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ Task creation failed: {response.status_code}")
        return
    
    task = response.json()
    print(f"✅ Task created: {task['title']}")
    
    # Start timer
    response = session.post(f"{BACKEND_URL}/tasks/{task['id']}/timer/start", headers=headers)
    if response.status_code != 200:
        print(f"❌ Timer start failed: {response.status_code}")
        return
    
    print(f"✅ Timer started")
    
    # Wait for 65 seconds (more than 1 minute)
    print("⏳ Waiting 65 seconds for meaningful duration...")
    time.sleep(65)
    
    # Stop timer with completion
    response = session.post(f"{BACKEND_URL}/tasks/{task['id']}/timer/stop?complete_task=true", headers=headers)
    if response.status_code != 200:
        print(f"❌ Timer stop failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return
    
    result = response.json()
    print(f"✅ Timer stopped with completion")
    print(f"   Session duration: {result['session_duration_seconds']} seconds")
    print(f"   Total elapsed seconds: {result['total_elapsed_seconds']}")
    print(f"   Total elapsed minutes: {result['total_elapsed_minutes']}")
    
    # Check the task in the response
    updated_task = result['task']
    print(f"   Task actual_duration: {updated_task.get('actual_duration', 'None')} minutes")
    print(f"   Task status: {updated_task.get('status', 'None')}")
    print(f"   Task completed_at: {updated_task.get('completed_at', 'None')}")
    
    # Verify calculation: 65 seconds = 1.08 minutes, should round to 1 minute
    expected_minutes = round(result['total_elapsed_seconds'] / 60)
    actual_minutes = updated_task.get('actual_duration', 0)
    
    if actual_minutes == expected_minutes and actual_minutes > 0:
        print(f"✅ Actual duration calculation correct: {actual_minutes} minutes")
    else:
        print(f"❌ Actual duration calculation incorrect: expected {expected_minutes}, got {actual_minutes}")
    
    # Check project analytics
    response = session.get(f"{BACKEND_URL}/projects/{project['id']}/analytics", headers=headers)
    if response.status_code == 200:
        analytics = response.json()
        print(f"✅ Project analytics:")
        print(f"   total_actual_time: {analytics.get('total_actual_time', 'None')} minutes")
        print(f"   completed_tasks: {analytics.get('completed_tasks', 'None')}")
        print(f"   progress_percentage: {analytics.get('progress_percentage', 'None')}%")
        
        if analytics.get('total_actual_time', 0) > 0:
            print(f"✅ Project analytics correctly tracking actual time")
        else:
            print(f"❌ Project analytics not tracking actual time")
    else:
        print(f"❌ Failed to get project analytics: {response.status_code}")
    
    # Cleanup
    session.delete(f"{BACKEND_URL}/tasks/{task['id']}", headers=headers)
    print(f"✅ Cleanup completed")

if __name__ == "__main__":
    test_longer_timer_duration()