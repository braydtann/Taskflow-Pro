#!/usr/bin/env python3
"""
Comprehensive Timer Functionality Testing Suite
Tests all timer endpoints with authentication and user access control
Focus: Timer start, pause, resume, stop, status tracking, and data persistence
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
import time
import random
import string

# Configuration
BACKEND_URL = "https://9b427bd1-3e37-401f-bf28-80af2a6bf86c.preview.emergentagent.com/api"
TIMEOUT = 30

class TimerFunctionalityTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = TIMEOUT
        self.test_data = {
            'users': [],
            'projects': [],
            'tasks': [],
            'tokens': {}
        }
        self.results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }

    def log_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
        
        if success:
            self.results['passed'] += 1
        else:
            self.results['failed'] += 1
            self.results['errors'].append(f"{test_name}: {message}")

    def generate_test_user_data(self, suffix: str = ""):
        """Generate realistic test user data"""
        random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return {
            "email": f"sarah.johnson{suffix}{random_id}@techcorp.com",
            "username": f"sarah_johnson{suffix}{random_id}",
            "full_name": f"Sarah Johnson{suffix}",
            "password": "SecurePass123!"
        }

    def test_user_registration_and_login(self):
        """Test user registration and login for timer testing"""
        print("\n=== Testing User Authentication Setup ===")
        
        # Create two test users for isolation testing
        for i, suffix in enumerate(["_timer1", "_timer2"]):
            user_data = self.generate_test_user_data(suffix)
            
            try:
                # Register user
                response = self.session.post(f"{BACKEND_URL}/auth/register", json=user_data)
                if response.status_code == 200:
                    token_data = response.json()
                    user_info = token_data['user']
                    self.test_data['users'].append(user_info)
                    self.test_data['tokens'][user_info['id']] = token_data['access_token']
                    self.log_result(f"User Registration {i+1}", True, f"Registered: {user_info['username']}")
                else:
                    self.log_result(f"User Registration {i+1}", False, f"HTTP {response.status_code}: {response.text}")
                    return False
            except Exception as e:
                self.log_result(f"User Registration {i+1}", False, f"Error: {str(e)}")
                return False
        
        return len(self.test_data['users']) == 2

    def create_test_projects_and_tasks(self):
        """Create test projects and tasks for timer testing"""
        print("\n=== Creating Test Projects and Tasks ===")
        
        if len(self.test_data['users']) < 2:
            self.log_result("Test Data Setup", False, "Insufficient users for testing")
            return False
        
        user1 = self.test_data['users'][0]
        user2 = self.test_data['users'][1]
        
        # Create projects for each user
        for i, user in enumerate([user1, user2]):
            headers = {"Authorization": f"Bearer {self.test_data['tokens'][user['id']]}"}
            
            project_data = {
                "name": f"Timer Testing Project {i+1}",
                "description": f"Project for testing timer functionality - User {i+1}",
                "collaborators": [],
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
            }
            
            try:
                response = self.session.post(f"{BACKEND_URL}/projects", json=project_data, headers=headers)
                if response.status_code == 200:
                    project = response.json()
                    self.test_data['projects'].append(project)
                    self.log_result(f"Create Project {i+1}", True, f"Created: {project['name']}")
                else:
                    self.log_result(f"Create Project {i+1}", False, f"HTTP {response.status_code}")
                    return False
            except Exception as e:
                self.log_result(f"Create Project {i+1}", False, f"Error: {str(e)}")
                return False
        
        # Create tasks for timer testing
        for i, (user, project) in enumerate(zip([user1, user2], self.test_data['projects'])):
            headers = {"Authorization": f"Bearer {self.test_data['tokens'][user['id']]}"}
            
            task_data = {
                "title": f"Implement Authentication System - Task {i+1}",
                "description": f"Build comprehensive user authentication with JWT tokens and password validation - User {i+1}",
                "priority": "high",
                "project_id": project['id'],
                "estimated_duration": 480,  # 8 hours in minutes
                "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                "assigned_users": [],
                "collaborators": [],
                "tags": ["authentication", "security", "backend"]
            }
            
            try:
                response = self.session.post(f"{BACKEND_URL}/tasks", json=task_data, headers=headers)
                if response.status_code == 200:
                    task = response.json()
                    self.test_data['tasks'].append(task)
                    self.log_result(f"Create Task {i+1}", True, f"Created: {task['title']}")
                else:
                    self.log_result(f"Create Task {i+1}", False, f"HTTP {response.status_code}")
                    return False
            except Exception as e:
                self.log_result(f"Create Task {i+1}", False, f"Error: {str(e)}")
                return False
        
        return len(self.test_data['tasks']) == 2

    def test_timer_start_functionality(self):
        """Test timer start functionality and automatic status change"""
        print("\n=== Testing Timer Start Functionality ===")
        
        if not self.test_data['tasks']:
            self.log_result("Timer Start Setup", False, "No tasks available for timer testing")
            return False
        
        user = self.test_data['users'][0]
        task = self.test_data['tasks'][0]
        headers = {"Authorization": f"Bearer {self.test_data['tokens'][user['id']]}"}
        
        try:
            # Start timer
            response = self.session.post(f"{BACKEND_URL}/tasks/{task['id']}/timer/start", headers=headers)
            if response.status_code == 200:
                result = response.json()
                updated_task = result['task']
                
                # Verify timer started
                if updated_task['is_timer_running'] and updated_task['timer_start_time']:
                    self.log_result("Timer Start", True, f"Timer started at: {result['timer_started_at']}")
                else:
                    self.log_result("Timer Start", False, "Timer not properly started")
                    return False
                
                # Verify status changed to in_progress
                if updated_task['status'] == 'in_progress':
                    self.log_result("Status Change to In Progress", True, "Task status automatically changed to in_progress")
                else:
                    self.log_result("Status Change to In Progress", False, f"Status is {updated_task['status']}, expected in_progress")
                    return False
                
                # Test starting timer again (should fail)
                response = self.session.post(f"{BACKEND_URL}/tasks/{task['id']}/timer/start", headers=headers)
                if response.status_code == 400:
                    self.log_result("Prevent Double Timer Start", True, "Properly prevents starting timer when already running")
                else:
                    self.log_result("Prevent Double Timer Start", False, f"Expected 400, got {response.status_code}")
                
                return True
            else:
                self.log_result("Timer Start", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Timer Start", False, f"Error: {str(e)}")
            return False

    def test_timer_pause_functionality(self):
        """Test timer pause functionality"""
        print("\n=== Testing Timer Pause Functionality ===")
        
        user = self.test_data['users'][0]
        task = self.test_data['tasks'][0]
        headers = {"Authorization": f"Bearer {self.test_data['tokens'][user['id']]}"}
        
        try:
            # Wait a moment for timer to accumulate some time
            time.sleep(2)
            
            # Pause timer
            response = self.session.post(f"{BACKEND_URL}/tasks/{task['id']}/timer/pause", headers=headers)
            if response.status_code == 200:
                result = response.json()
                updated_task = result['task']
                
                # Verify timer paused
                if not updated_task['is_timer_running'] and updated_task['timer_start_time'] is None:
                    self.log_result("Timer Pause", True, f"Timer paused. Session duration: {result['session_duration_seconds']}s")
                else:
                    self.log_result("Timer Pause", False, "Timer not properly paused")
                    return False
                
                # Verify elapsed time accumulated
                if updated_task['timer_elapsed_seconds'] > 0:
                    self.log_result("Elapsed Time Accumulation", True, f"Accumulated {updated_task['timer_elapsed_seconds']} seconds")
                else:
                    self.log_result("Elapsed Time Accumulation", False, "No elapsed time accumulated")
                    return False
                
                # Verify status remains in_progress
                if updated_task['status'] == 'in_progress':
                    self.log_result("Status Remains In Progress", True, "Task status correctly remains in_progress when paused")
                else:
                    self.log_result("Status Remains In Progress", False, f"Status changed to {updated_task['status']}")
                    return False
                
                # Verify timer session recorded
                if len(updated_task['timer_sessions']) > 0:
                    session = updated_task['timer_sessions'][0]
                    if 'start_time' in session and 'end_time' in session and 'duration_seconds' in session:
                        self.log_result("Timer Session Recording", True, f"Session recorded: {session['duration_seconds']}s")
                    else:
                        self.log_result("Timer Session Recording", False, "Session data incomplete")
                        return False
                else:
                    self.log_result("Timer Session Recording", False, "No timer session recorded")
                    return False
                
                # Test pausing already paused timer (should fail)
                response = self.session.post(f"{BACKEND_URL}/tasks/{task['id']}/timer/pause", headers=headers)
                if response.status_code == 400:
                    self.log_result("Prevent Double Pause", True, "Properly prevents pausing already paused timer")
                else:
                    self.log_result("Prevent Double Pause", False, f"Expected 400, got {response.status_code}")
                
                return True
            else:
                self.log_result("Timer Pause", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Timer Pause", False, f"Error: {str(e)}")
            return False

    def test_timer_resume_functionality(self):
        """Test timer resume functionality"""
        print("\n=== Testing Timer Resume Functionality ===")
        
        user = self.test_data['users'][0]
        task = self.test_data['tasks'][0]
        headers = {"Authorization": f"Bearer {self.test_data['tokens'][user['id']]}"}
        
        try:
            # Resume timer
            response = self.session.post(f"{BACKEND_URL}/tasks/{task['id']}/timer/resume", headers=headers)
            if response.status_code == 200:
                result = response.json()
                updated_task = result['task']
                
                # Verify timer resumed
                if updated_task['is_timer_running'] and updated_task['timer_start_time']:
                    self.log_result("Timer Resume", True, f"Timer resumed at: {result['timer_resumed_at']}")
                else:
                    self.log_result("Timer Resume", False, "Timer not properly resumed")
                    return False
                
                # Verify status is in_progress
                if updated_task['status'] == 'in_progress':
                    self.log_result("Status Remains In Progress on Resume", True, "Task status correctly remains in_progress")
                else:
                    self.log_result("Status Remains In Progress on Resume", False, f"Status is {updated_task['status']}")
                    return False
                
                # Verify previous elapsed time preserved
                if updated_task['timer_elapsed_seconds'] > 0:
                    self.log_result("Previous Elapsed Time Preserved", True, f"Previous elapsed time: {updated_task['timer_elapsed_seconds']}s")
                else:
                    self.log_result("Previous Elapsed Time Preserved", False, "Previous elapsed time lost")
                    return False
                
                # Test resuming already running timer (should fail)
                response = self.session.post(f"{BACKEND_URL}/tasks/{task['id']}/timer/resume", headers=headers)
                if response.status_code == 400:
                    self.log_result("Prevent Double Resume", True, "Properly prevents resuming already running timer")
                else:
                    self.log_result("Prevent Double Resume", False, f"Expected 400, got {response.status_code}")
                
                return True
            else:
                self.log_result("Timer Resume", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Timer Resume", False, f"Error: {str(e)}")
            return False

    def test_timer_status_tracking(self):
        """Test real-time timer status retrieval"""
        print("\n=== Testing Timer Status Tracking ===")
        
        user = self.test_data['users'][0]
        task = self.test_data['tasks'][0]
        headers = {"Authorization": f"Bearer {self.test_data['tokens'][user['id']]}"}
        
        try:
            # Wait a moment for timer to accumulate time
            time.sleep(2)
            
            # Get timer status
            response = self.session.get(f"{BACKEND_URL}/tasks/{task['id']}/timer/status", headers=headers)
            if response.status_code == 200:
                status = response.json()
                
                # Verify status structure
                required_fields = ['task_id', 'is_timer_running', 'elapsed_seconds', 'current_session_seconds', 'total_current_seconds', 'total_current_minutes']
                if all(field in status for field in required_fields):
                    self.log_result("Timer Status Structure", True, "All required status fields present")
                else:
                    missing = [f for f in required_fields if f not in status]
                    self.log_result("Timer Status Structure", False, f"Missing fields: {missing}")
                    return False
                
                # Verify timer is running
                if status['is_timer_running']:
                    self.log_result("Timer Running Status", True, "Timer correctly reported as running")
                else:
                    self.log_result("Timer Running Status", False, "Timer not reported as running")
                    return False
                
                # Verify real-time calculation
                if status['current_session_seconds'] > 0:
                    self.log_result("Real-time Session Calculation", True, f"Current session: {status['current_session_seconds']}s")
                else:
                    self.log_result("Real-time Session Calculation", False, "No current session time calculated")
                    return False
                
                # Verify total time calculation
                if status['total_current_seconds'] > status['elapsed_seconds']:
                    self.log_result("Total Time Calculation", True, f"Total: {status['total_current_seconds']}s, Previous: {status['elapsed_seconds']}s")
                else:
                    self.log_result("Total Time Calculation", False, "Total time calculation incorrect")
                    return False
                
                # Verify minutes conversion
                expected_minutes = round(status['total_current_seconds'] / 60, 2)
                if abs(status['total_current_minutes'] - expected_minutes) < 0.01:
                    self.log_result("Minutes Conversion", True, f"Correctly converted to {status['total_current_minutes']} minutes")
                else:
                    self.log_result("Minutes Conversion", False, f"Expected {expected_minutes}, got {status['total_current_minutes']}")
                    return False
                
                return True
            else:
                self.log_result("Timer Status", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Timer Status", False, f"Error: {str(e)}")
            return False

    def test_timer_stop_functionality(self):
        """Test timer stop functionality with and without task completion"""
        print("\n=== Testing Timer Stop Functionality ===")
        
        user = self.test_data['users'][0]
        task = self.test_data['tasks'][0]
        headers = {"Authorization": f"Bearer {self.test_data['tokens'][user['id']]}"}
        
        try:
            # Wait a moment for timer to accumulate more time
            time.sleep(2)
            
            # Stop timer without completing task
            response = self.session.post(f"{BACKEND_URL}/tasks/{task['id']}/timer/stop?complete_task=false", headers=headers)
            if response.status_code == 200:
                result = response.json()
                updated_task = result['task']
                
                # Verify timer stopped
                if not updated_task['is_timer_running'] and updated_task['timer_start_time'] is None:
                    self.log_result("Timer Stop", True, f"Timer stopped. Total elapsed: {result['total_elapsed_minutes']} minutes")
                else:
                    self.log_result("Timer Stop", False, "Timer not properly stopped")
                    return False
                
                # Verify actual_duration updated
                if updated_task['actual_duration'] and updated_task['actual_duration'] > 0:
                    self.log_result("Actual Duration Update", True, f"Actual duration: {updated_task['actual_duration']} minutes")
                else:
                    self.log_result("Actual Duration Update", False, "Actual duration not updated")
                    return False
                
                # Verify task not completed (since complete_task=false)
                if updated_task['status'] == 'in_progress':
                    self.log_result("Task Status Without Completion", True, "Task remains in_progress when not completing")
                else:
                    self.log_result("Task Status Without Completion", False, f"Status changed to {updated_task['status']}")
                    return False
                
                # Verify multiple timer sessions recorded
                if len(updated_task['timer_sessions']) >= 2:
                    self.log_result("Multiple Timer Sessions", True, f"Recorded {len(updated_task['timer_sessions'])} timer sessions")
                else:
                    self.log_result("Multiple Timer Sessions", False, f"Expected >= 2 sessions, got {len(updated_task['timer_sessions'])}")
                    return False
                
                return True
            else:
                self.log_result("Timer Stop", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Timer Stop", False, f"Error: {str(e)}")
            return False

    def test_timer_stop_with_completion(self):
        """Test timer stop with task completion"""
        print("\n=== Testing Timer Stop with Task Completion ===")
        
        user = self.test_data['users'][0]
        task = self.test_data['tasks'][0]
        headers = {"Authorization": f"Bearer {self.test_data['tokens'][user['id']]}"}
        
        try:
            # Start timer again for completion test
            response = self.session.post(f"{BACKEND_URL}/tasks/{task['id']}/timer/start", headers=headers)
            if response.status_code != 200:
                self.log_result("Timer Restart for Completion", False, f"Could not restart timer: {response.status_code}")
                return False
            
            # Wait a moment
            time.sleep(2)
            
            # Stop timer with task completion
            response = self.session.post(f"{BACKEND_URL}/tasks/{task['id']}/timer/stop?complete_task=true", headers=headers)
            if response.status_code == 200:
                result = response.json()
                updated_task = result['task']
                
                # Verify timer stopped
                if not updated_task['is_timer_running']:
                    self.log_result("Timer Stop with Completion", True, "Timer stopped successfully")
                else:
                    self.log_result("Timer Stop with Completion", False, "Timer still running")
                    return False
                
                # Verify task completed
                if updated_task['status'] == 'completed' and updated_task['completed_at']:
                    self.log_result("Task Completion", True, f"Task completed at: {updated_task['completed_at']}")
                else:
                    self.log_result("Task Completion", False, f"Task not completed. Status: {updated_task['status']}")
                    return False
                
                # Verify actual duration updated with all sessions
                if updated_task['actual_duration'] and updated_task['actual_duration'] > 0:
                    self.log_result("Final Actual Duration", True, f"Final duration: {updated_task['actual_duration']} minutes")
                else:
                    self.log_result("Final Actual Duration", False, "Final duration not set")
                    return False
                
                return True
            else:
                self.log_result("Timer Stop with Completion", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Timer Stop with Completion", False, f"Error: {str(e)}")
            return False

    def test_timer_data_persistence(self):
        """Test timer data persistence and session history"""
        print("\n=== Testing Timer Data Persistence ===")
        
        user = self.test_data['users'][0]
        task = self.test_data['tasks'][0]
        headers = {"Authorization": f"Bearer {self.test_data['tokens'][user['id']]}"}
        
        try:
            # Get final task state
            response = self.session.get(f"{BACKEND_URL}/tasks/{task['id']}", headers=headers)
            if response.status_code == 200:
                final_task = response.json()
                
                # Verify timer sessions persisted
                if len(final_task['timer_sessions']) > 0:
                    sessions = final_task['timer_sessions']
                    self.log_result("Timer Sessions Persistence", True, f"Persisted {len(sessions)} timer sessions")
                    
                    # Verify session data structure
                    session = sessions[0]
                    required_fields = ['start_time', 'end_time', 'duration_seconds', 'session_type']
                    if all(field in session for field in required_fields):
                        self.log_result("Session Data Structure", True, "Session data properly structured")
                    else:
                        missing = [f for f in required_fields if f not in session]
                        self.log_result("Session Data Structure", False, f"Missing fields: {missing}")
                        return False
                    
                    # Verify total duration calculation
                    total_session_seconds = sum(s['duration_seconds'] for s in sessions)
                    if abs(final_task['timer_elapsed_seconds'] - total_session_seconds) <= 1:  # Allow 1 second tolerance
                        self.log_result("Total Duration Calculation", True, f"Total: {final_task['timer_elapsed_seconds']}s matches sessions")
                    else:
                        self.log_result("Total Duration Calculation", False, f"Mismatch: {final_task['timer_elapsed_seconds']}s vs {total_session_seconds}s")
                        return False
                else:
                    self.log_result("Timer Sessions Persistence", False, "No timer sessions persisted")
                    return False
                
                # Verify actual_duration matches timer data
                expected_minutes = round(final_task['timer_elapsed_seconds'] / 60)
                if final_task['actual_duration'] == expected_minutes:
                    self.log_result("Actual Duration Accuracy", True, f"Actual duration {final_task['actual_duration']} minutes matches timer data")
                else:
                    self.log_result("Actual Duration Accuracy", False, f"Expected {expected_minutes}, got {final_task['actual_duration']}")
                    return False
                
                return True
            else:
                self.log_result("Timer Data Persistence", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Timer Data Persistence", False, f"Error: {str(e)}")
            return False

    def test_timer_user_authentication_integration(self):
        """Test timer endpoints require authentication and respect user access"""
        print("\n=== Testing Timer Authentication Integration ===")
        
        user1 = self.test_data['users'][0]
        user2 = self.test_data['users'][1]
        task1 = self.test_data['tasks'][0]  # Owned by user1
        task2 = self.test_data['tasks'][1]  # Owned by user2
        
        headers1 = {"Authorization": f"Bearer {self.test_data['tokens'][user1['id']]}"}
        headers2 = {"Authorization": f"Bearer {self.test_data['tokens'][user2['id']]}"}
        
        try:
            # Test unauthenticated access (should fail)
            response = self.session.post(f"{BACKEND_URL}/tasks/{task1['id']}/timer/start")
            if response.status_code in [401, 403]:
                self.log_result("Unauthenticated Timer Access", True, "Properly blocks unauthenticated timer access")
            else:
                self.log_result("Unauthenticated Timer Access", False, f"Expected 401/403, got {response.status_code}")
                return False
            
            # Test cross-user access (user2 trying to access user1's task timer)
            response = self.session.post(f"{BACKEND_URL}/tasks/{task1['id']}/timer/start", headers=headers2)
            if response.status_code == 404:
                self.log_result("Cross-User Timer Access", True, "Properly blocks cross-user timer access")
            else:
                self.log_result("Cross-User Timer Access", False, f"Expected 404, got {response.status_code}")
                return False
            
            # Test legitimate access (user2 accessing their own task)
            response = self.session.post(f"{BACKEND_URL}/tasks/{task2['id']}/timer/start", headers=headers2)
            if response.status_code == 200:
                self.log_result("Legitimate Timer Access", True, "User can access their own task timer")
                
                # Clean up - stop the timer
                self.session.post(f"{BACKEND_URL}/tasks/{task2['id']}/timer/stop", headers=headers2)
            else:
                self.log_result("Legitimate Timer Access", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            return True
        except Exception as e:
            self.log_result("Timer Authentication Integration", False, f"Error: {str(e)}")
            return False

    def test_timer_project_analytics_integration(self):
        """Test timer functionality integration with project analytics"""
        print("\n=== Testing Timer-Project Analytics Integration ===")
        
        user = self.test_data['users'][0]
        project = self.test_data['projects'][0]
        headers = {"Authorization": f"Bearer {self.test_data['tokens'][user['id']]}"}
        
        try:
            # Get project analytics
            response = self.session.get(f"{BACKEND_URL}/projects/{project['id']}/analytics", headers=headers)
            if response.status_code == 200:
                analytics = response.json()
                
                # Verify completed task count updated
                if analytics['completed_tasks'] > 0:
                    self.log_result("Project Completed Task Count", True, f"Project shows {analytics['completed_tasks']} completed tasks")
                else:
                    self.log_result("Project Completed Task Count", False, "Completed task count not updated")
                    return False
                
                # Verify actual time tracking
                if analytics['total_actual_time'] > 0:
                    self.log_result("Project Actual Time Tracking", True, f"Project tracks {analytics['total_actual_time']} minutes of actual time")
                else:
                    self.log_result("Project Actual Time Tracking", False, "Actual time not tracked in project analytics")
                    return False
                
                # Verify progress percentage calculation
                if analytics['progress_percentage'] > 0:
                    self.log_result("Project Progress Calculation", True, f"Project progress: {analytics['progress_percentage']}%")
                else:
                    self.log_result("Project Progress Calculation", False, "Progress percentage not calculated")
                    return False
                
                return True
            else:
                self.log_result("Timer-Project Analytics Integration", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Timer-Project Analytics Integration", False, f"Error: {str(e)}")
            return False

    def test_timer_edge_cases(self):
        """Test timer edge cases and error handling"""
        print("\n=== Testing Timer Edge Cases ===")
        
        user = self.test_data['users'][1]
        headers = {"Authorization": f"Bearer {self.test_data['tokens'][user['id']]}"}
        
        try:
            # Test timer operations on non-existent task
            fake_task_id = str(uuid.uuid4())
            response = self.session.post(f"{BACKEND_URL}/tasks/{fake_task_id}/timer/start", headers=headers)
            if response.status_code == 404:
                self.log_result("Non-existent Task Timer", True, "Properly handles non-existent task")
            else:
                self.log_result("Non-existent Task Timer", False, f"Expected 404, got {response.status_code}")
                return False
            
            # Test timer status on non-existent task
            response = self.session.get(f"{BACKEND_URL}/tasks/{fake_task_id}/timer/status", headers=headers)
            if response.status_code == 404:
                self.log_result("Non-existent Task Timer Status", True, "Properly handles non-existent task status request")
            else:
                self.log_result("Non-existent Task Timer Status", False, f"Expected 404, got {response.status_code}")
                return False
            
            # Test stopping non-running timer
            task = self.test_data['tasks'][1]  # User2's task
            response = self.session.post(f"{BACKEND_URL}/tasks/{task['id']}/timer/stop", headers=headers)
            if response.status_code == 400:
                self.log_result("Stop Non-running Timer", True, "Properly prevents stopping non-running timer")
            else:
                self.log_result("Stop Non-running Timer", False, f"Expected 400, got {response.status_code}")
                return False
            
            return True
        except Exception as e:
            self.log_result("Timer Edge Cases", False, f"Error: {str(e)}")
            return False

    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n=== Cleaning Up Test Data ===")
        
        # Delete test tasks
        for i, (task, user) in enumerate(zip(self.test_data['tasks'], self.test_data['users'])):
            try:
                headers = {"Authorization": f"Bearer {self.test_data['tokens'][user['id']]}"}
                response = self.session.delete(f"{BACKEND_URL}/tasks/{task['id']}", headers=headers)
                if response.status_code == 200:
                    print(f"✅ Deleted task: {task['title']}")
                else:
                    print(f"❌ Failed to delete task: {task['title']}")
            except Exception as e:
                print(f"❌ Error deleting task {task['title']}: {str(e)}")
        
        print(f"Cleanup completed")

    def run_all_tests(self):
        """Run all timer functionality tests"""
        print("🚀 Starting Comprehensive Timer Functionality Testing Suite")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 70)
        
        # Test sequence
        tests = [
            self.test_user_registration_and_login,
            self.create_test_projects_and_tasks,
            self.test_timer_start_functionality,
            self.test_timer_pause_functionality,
            self.test_timer_resume_functionality,
            self.test_timer_status_tracking,
            self.test_timer_stop_functionality,
            self.test_timer_stop_with_completion,
            self.test_timer_data_persistence,
            self.test_timer_user_authentication_integration,
            self.test_timer_project_analytics_integration,
            self.test_timer_edge_cases
        ]
        
        for test in tests:
            try:
                test()
                time.sleep(1)  # Brief pause between tests
            except Exception as e:
                self.log_result(test.__name__, False, f"Test execution error: {str(e)}")
        
        # Cleanup
        self.cleanup_test_data()
        
        # Final results
        print("\n" + "=" * 70)
        print("🏁 FINAL TIMER FUNCTIONALITY TEST RESULTS")
        print("=" * 70)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Success Rate: {(self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100):.1f}%")
        
        if self.results['errors']:
            print("\n🔍 FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

if __name__ == "__main__":
    tester = TimerFunctionalityTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All timer functionality tests passed! Timer system is working correctly.")
        exit(0)
    else:
        print(f"\n⚠️  {tester.results['failed']} timer tests failed. Check the issues above.")
        exit(1)