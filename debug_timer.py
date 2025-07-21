#!/usr/bin/env python3
"""
Debug Timer Actual Duration Issue
Focused test to investigate the actual_duration field update problem
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
import time
import random
import string

# Configuration
BACKEND_URL = "https://2014dd9e-36f3-46e1-9c60-eaf1580b2c68.preview.emergentagent.com/api"
TIMEOUT = 30

def generate_test_user_data():
    """Generate realistic test user data"""
    random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return {
        "email": f"debug.user{random_id}@techcorp.com",
        "username": f"debug_user{random_id}",
        "full_name": f"Debug User",
        "password": "SecurePass123!"
    }

def debug_timer_actual_duration():
    """Debug the actual_duration field issue"""
    session = requests.Session()
    session.timeout = TIMEOUT
    
    print("🔍 Debugging Timer Actual Duration Issue")
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
        "name": "Debug Timer Project",
        "description": "Project for debugging timer actual duration",
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
        "title": "Debug Timer Task",
        "description": "Task for debugging timer actual duration",
        "priority": "high",
        "project_id": project['id'],
        "estimated_duration": 60,  # 1 hour
        "assigned_users": [],
        "collaborators": [],
        "tags": ["debug", "timer"]
    }
    
    response = session.post(f"{BACKEND_URL}/tasks", json=task_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ Task creation failed: {response.status_code}")
        return
    
    task = response.json()
    print(f"✅ Task created: {task['title']}")
    print(f"   Initial actual_duration: {task.get('actual_duration', 'None')}")
    
    # Start timer
    response = session.post(f"{BACKEND_URL}/tasks/{task['id']}/timer/start", headers=headers)
    if response.status_code != 200:
        print(f"❌ Timer start failed: {response.status_code}")
        return
    
    result = response.json()
    print(f"✅ Timer started")
    print(f"   Timer running: {result['task']['is_timer_running']}")
    print(f"   Timer start time: {result['task']['timer_start_time']}")
    
    # Wait for some time
    print("⏳ Waiting 5 seconds...")
    time.sleep(5)
    
    # Check timer status
    response = session.get(f"{BACKEND_URL}/tasks/{task['id']}/timer/status", headers=headers)
    if response.status_code == 200:
        status = response.json()
        print(f"✅ Timer status:")
        print(f"   Running: {status['is_timer_running']}")
        print(f"   Current session seconds: {status['current_session_seconds']}")
        print(f"   Total current seconds: {status['total_current_seconds']}")
        print(f"   Total current minutes: {status['total_current_minutes']}")
    
    # Stop timer and check response
    response = session.post(f"{BACKEND_URL}/tasks/{task['id']}/timer/stop?complete_task=false", headers=headers)
    if response.status_code != 200:
        print(f"❌ Timer stop failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return
    
    result = response.json()
    print(f"✅ Timer stopped")
    print(f"   Session duration: {result['session_duration_seconds']} seconds")
    print(f"   Total elapsed seconds: {result['total_elapsed_seconds']}")
    print(f"   Total elapsed minutes: {result['total_elapsed_minutes']}")
    
    # Check the task in the response
    updated_task = result['task']
    print(f"   Task actual_duration in response: {updated_task.get('actual_duration', 'None')}")
    print(f"   Task timer_elapsed_seconds: {updated_task.get('timer_elapsed_seconds', 'None')}")
    
    # Get task directly to verify persistence
    response = session.get(f"{BACKEND_URL}/tasks/{task['id']}", headers=headers)
    if response.status_code == 200:
        fresh_task = response.json()
        print(f"✅ Fresh task retrieved:")
        print(f"   actual_duration: {fresh_task.get('actual_duration', 'None')}")
        print(f"   timer_elapsed_seconds: {fresh_task.get('timer_elapsed_seconds', 'None')}")
        print(f"   is_timer_running: {fresh_task.get('is_timer_running', 'None')}")
        print(f"   timer_sessions count: {len(fresh_task.get('timer_sessions', []))}")
        
        if fresh_task.get('timer_sessions'):
            print(f"   First session: {fresh_task['timer_sessions'][0]}")
    else:
        print(f"❌ Failed to retrieve fresh task: {response.status_code}")
    
    # Check project analytics
    response = session.get(f"{BACKEND_URL}/projects/{project['id']}/analytics", headers=headers)
    if response.status_code == 200:
        analytics = response.json()
        print(f"✅ Project analytics:")
        print(f"   total_actual_time: {analytics.get('total_actual_time', 'None')}")
        print(f"   total_estimated_time: {analytics.get('total_estimated_time', 'None')}")
        print(f"   completed_tasks: {analytics.get('completed_tasks', 'None')}")
    else:
        print(f"❌ Failed to get project analytics: {response.status_code}")
    
    # Cleanup
    session.delete(f"{BACKEND_URL}/tasks/{task['id']}", headers=headers)
    print(f"✅ Cleanup completed")

if __name__ == "__main__":
    debug_timer_actual_duration()