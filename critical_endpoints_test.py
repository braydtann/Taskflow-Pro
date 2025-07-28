#!/usr/bin/env python3
"""
Critical Endpoints Testing - Focus on the specific endpoints that were failing
"""

import requests
import json
import uuid
from datetime import datetime, timedelta

# Configuration
BACKEND_URL = "https://34c353d5-13c6-4f3d-b463-fb80eaba5a2e.preview.emergentagent.com/api"
TIMEOUT = 30

class CriticalEndpointsTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = TIMEOUT
        self.results = {'passed': 0, 'failed': 0, 'errors': []}

    def log_result(self, test_name: str, success: bool, message: str = ""):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
        
        if success:
            self.results['passed'] += 1
        else:
            self.results['failed'] += 1
            self.results['errors'].append(f"{test_name}: {message}")

    def setup_test_environment(self):
        """Setup test environment with users, projects, and tasks"""
        print("\n=== Setting Up Test Environment ===")
        
        # Create PM user
        pm_data = {
            "email": f"pm_critical_{uuid.uuid4().hex[:8]}@example.com",
            "username": f"pm_critical_{uuid.uuid4().hex[:6]}",
            "full_name": "Critical Test PM",
            "password": "SecurePass123!",
            "role": "project_manager"
        }
        
        response = self.session.post(f"{BACKEND_URL}/auth/register", json=pm_data)
        if response.status_code != 200:
            print(f"❌ Failed to create PM user: {response.status_code}")
            return None
        
        pm_token_data = response.json()
        pm_headers = {'Authorization': f"Bearer {pm_token_data['access_token']}"}
        
        # Create regular user
        user_data = {
            "email": f"user_critical_{uuid.uuid4().hex[:8]}@example.com",
            "username": f"user_critical_{uuid.uuid4().hex[:6]}",
            "full_name": "Critical Test User",
            "password": "SecurePass123!"
        }
        
        response = self.session.post(f"{BACKEND_URL}/auth/register", json=user_data)
        if response.status_code != 200:
            print(f"❌ Failed to create regular user: {response.status_code}")
            return None
        
        user_token_data = response.json()
        user_headers = {'Authorization': f"Bearer {user_token_data['access_token']}"}
        
        # Create project with PM assignment
        project_data = {
            "name": "Critical Test Project",
            "description": "Project for testing critical endpoints",
            "project_managers": [pm_token_data['user']['id']],
            "collaborators": [user_token_data['user']['id']],
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        
        response = self.session.post(f"{BACKEND_URL}/projects", json=project_data, headers=user_headers)
        if response.status_code != 200:
            print(f"❌ Failed to create project: {response.status_code}")
            return None
        
        project = response.json()
        
        # Create tasks with overdue scenarios
        tasks = []
        task_scenarios = [
            {
                "title": "Overdue Critical Task",
                "due_date": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                "status": "in_progress"
            },
            {
                "title": "Future Task",
                "due_date": (datetime.utcnow() + timedelta(days=5)).isoformat(),
                "status": "todo"
            },
            {
                "title": "Completed Overdue Task",
                "due_date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "status": "completed"
            }
        ]
        
        for task_data in task_scenarios:
            task_payload = {
                "title": task_data["title"],
                "description": "Critical endpoint test task",
                "priority": "high",
                "project_id": project['id'],
                "due_date": task_data["due_date"],
                "estimated_duration": 120
            }
            
            response = self.session.post(f"{BACKEND_URL}/tasks", json=task_payload, headers=user_headers)
            if response.status_code == 200:
                task = response.json()
                
                # Update status if needed
                if task_data["status"] != "todo":
                    update_data = {"status": task_data["status"]}
                    if task_data["status"] == "completed":
                        update_data["completed_at"] = datetime.utcnow().isoformat()
                    
                    self.session.put(f"{BACKEND_URL}/tasks/{task['id']}", json=update_data, headers=user_headers)
                
                tasks.append(task)
        
        print(f"✅ Setup complete: PM user, regular user, 1 project, {len(tasks)} tasks")
        
        return {
            'pm_headers': pm_headers,
            'user_headers': user_headers,
            'project': project,
            'tasks': tasks,
            'pm_user': pm_token_data['user'],
            'regular_user': user_token_data['user']
        }

    def test_critical_endpoints(self):
        """Test the 5 critical endpoints mentioned in the review request"""
        print("\n🎯 TESTING CRITICAL ENDPOINTS")
        print("=" * 50)
        
        env = self.setup_test_environment()
        if not env:
            print("❌ Failed to setup test environment")
            return False
        
        # 1. Test GET /api/pm/dashboard
        print("\n1. Testing GET /api/pm/dashboard")
        response = self.session.get(f"{BACKEND_URL}/pm/dashboard", headers=env['pm_headers'])
        
        if response.status_code == 200:
            dashboard = response.json()
            self.log_result("PM Dashboard Endpoint", True, 
                          f"HTTP 200 - Contains {len(dashboard.get('projects', []))} projects")
            
            # Check for datetime-related fields that could cause parsing issues
            overview = dashboard.get('overview', {})
            if 'total_tasks' in overview and 'total_projects' in overview:
                self.log_result("PM Dashboard Data Integrity", True, 
                              f"Overview data: {overview.get('total_tasks')} tasks, {overview.get('total_projects')} projects")
            else:
                self.log_result("PM Dashboard Data Integrity", False, "Missing overview data")
        else:
            self.log_result("PM Dashboard Endpoint", False, 
                          f"HTTP {response.status_code} - Expected 200. Response: {response.text[:200]}")
        
        # 2. Test GET /api/pm/projects
        print("\n2. Testing GET /api/pm/projects")
        response = self.session.get(f"{BACKEND_URL}/pm/projects", headers=env['pm_headers'])
        
        if response.status_code == 200:
            projects = response.json()
            self.log_result("PM Projects Endpoint", True, 
                          f"HTTP 200 - Retrieved {len(projects)} projects")
            
            if projects:
                project = projects[0]
                datetime_fields = ['created_at', 'updated_at']
                present_fields = [f for f in datetime_fields if f in project and project[f]]
                self.log_result("PM Projects DateTime Fields", True, 
                              f"DateTime fields present: {present_fields}")
        else:
            self.log_result("PM Projects Endpoint", False, 
                          f"HTTP {response.status_code} - Expected 200. Response: {response.text[:200]}")
        
        # 3. Test POST /api/tasks
        print("\n3. Testing POST /api/tasks")
        task_data = {
            "title": "Critical Endpoint Test Task",
            "description": "Testing task creation with datetime parsing",
            "priority": "high",
            "project_id": env['project']['id'],
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "estimated_duration": 180
        }
        
        response = self.session.post(f"{BACKEND_URL}/tasks", json=task_data, headers=env['user_headers'])
        
        if response.status_code == 200:
            task = response.json()
            self.log_result("Task Creation Endpoint", True, 
                          f"HTTP 200 - Created task: {task['title']}")
            
            # Verify datetime parsing worked
            if task.get('due_date') and task.get('created_at'):
                self.log_result("Task DateTime Parsing", True, "Due date and created_at properly set")
            else:
                self.log_result("Task DateTime Parsing", False, "DateTime fields missing or invalid")
        else:
            self.log_result("Task Creation Endpoint", False, 
                          f"HTTP {response.status_code} - Expected 200. Response: {response.text[:200]}")
        
        # 4. Test PUT /api/pm/projects/{project_id}/status
        print("\n4. Testing PUT /api/pm/projects/{project_id}/status")
        status_data = {"status": "on_hold"}
        
        response = self.session.put(
            f"{BACKEND_URL}/pm/projects/{env['project']['id']}/status", 
            json=status_data, 
            headers=env['pm_headers']
        )
        
        if response.status_code == 200:
            updated_project = response.json()
            self.log_result("PM Project Status Update", True, 
                          f"HTTP 200 - Status updated")
            
            # Verify datetime fields are preserved
            if updated_project.get('updated_at'):
                self.log_result("PM Status Update DateTime Preservation", True, 
                              "updated_at field preserved after status change")
            else:
                self.log_result("PM Status Update DateTime Preservation", False, 
                              "updated_at field missing after status change")
        else:
            self.log_result("PM Project Status Update", False, 
                          f"HTTP {response.status_code} - Expected 200. Response: {response.text[:200]}")
        
        # 5. Test GET /api/pm/projects/{project_id}/team
        print("\n5. Testing GET /api/pm/projects/{project_id}/team")
        response = self.session.get(
            f"{BACKEND_URL}/pm/projects/{env['project']['id']}/team", 
            headers=env['pm_headers']
        )
        
        if response.status_code == 200:
            team_data = response.json()
            self.log_result("PM Project Team Workload", True, 
                          f"HTTP 200 - Retrieved team data for {len(team_data)} members")
            
            # Check if workload calculations work (this involves datetime parsing for overdue tasks)
            if team_data:
                member = team_data[0]
                if 'username' in member or 'user_id' in member:
                    self.log_result("PM Team Workload Data Structure", True, 
                                  "Team member data contains user identification")
                else:
                    self.log_result("PM Team Workload Data Structure", False, 
                                  "Team member data missing user identification")
        else:
            self.log_result("PM Project Team Workload", False, 
                          f"HTTP {response.status_code} - Expected 200. Response: {response.text[:200]}")
        
        return True

    def test_overdue_calculation_robustness(self):
        """Test overdue calculation with various datetime scenarios"""
        print("\n🕒 TESTING OVERDUE CALCULATION ROBUSTNESS")
        print("=" * 50)
        
        env = self.setup_test_environment()
        if not env:
            return False
        
        # Test analytics dashboard which uses overdue calculations
        response = self.session.get(f"{BACKEND_URL}/analytics/dashboard", headers=env['user_headers'])
        
        if response.status_code == 200:
            analytics = response.json()
            overview = analytics.get('overview', {})
            
            self.log_result("Analytics Dashboard with Overdue Tasks", True, 
                          f"HTTP 200 - Dashboard loaded successfully")
            
            if 'overdue_tasks' in overview:
                overdue_count = overview['overdue_tasks']
                self.log_result("Overdue Task Count Calculation", True, 
                              f"Overdue tasks: {overdue_count}")
                
                # We created 1 overdue in_progress task, so should have at least 1
                if overdue_count >= 1:
                    self.log_result("Overdue Task Logic Verification", True, 
                                  "Overdue count matches expected (≥1)")
                else:
                    self.log_result("Overdue Task Logic Verification", False, 
                                  f"Expected ≥1 overdue task, got {overdue_count}")
            else:
                self.log_result("Overdue Task Count Calculation", False, 
                              "overdue_tasks field missing from overview")
        else:
            self.log_result("Analytics Dashboard with Overdue Tasks", False, 
                          f"HTTP {response.status_code} - Dashboard failed to load")
        
        return True

    def run_all_tests(self):
        """Run all critical endpoint tests"""
        print("🚨 CRITICAL ENDPOINTS TESTING")
        print("Testing the specific endpoints that were failing before datetime parsing fixes")
        print("=" * 80)
        
        self.test_critical_endpoints()
        self.test_overdue_calculation_robustness()
        
        # Print results
        print("\n" + "=" * 80)
        print("🏁 CRITICAL ENDPOINTS TEST RESULTS")
        print("=" * 80)
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        
        if self.results['passed'] + self.results['failed'] > 0:
            success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed'])) * 100
            print(f"📊 SUCCESS RATE: {success_rate:.1f}%")
        
        if self.results['errors']:
            print(f"\n🚨 FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        print("\n🎯 CRITICAL ENDPOINT STATUS:")
        critical_endpoints = [
            "PM Dashboard Endpoint",
            "PM Projects Endpoint", 
            "Task Creation Endpoint",
            "PM Project Status Update",
            "PM Project Team Workload"
        ]
        
        for endpoint in critical_endpoints:
            status = "✅ WORKING" if any(endpoint in error for error in self.results['errors']) == False else "❌ FAILING"
            print(f"   {status}: {endpoint}")
        
        return self.results['failed'] == 0

if __name__ == "__main__":
    tester = CriticalEndpointsTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)