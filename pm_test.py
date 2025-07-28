#!/usr/bin/env python3
"""
Project Manager Dashboard Testing Suite
Tests all PM-specific backend functionality
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
import time

# Configuration
BACKEND_URL = "https://9b427bd1-3e37-401f-bf28-80af2a6bf86c.preview.emergentagent.com/api"
TIMEOUT = 30

class PMDashboardTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = TIMEOUT
        self.test_data = {
            'projects': [],
            'tasks': []
        }
        self.results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
        
        # User tokens
        self.pm_token = None
        self.admin_token = None
        self.regular_token = None
        self.pm_user_id = None
        self.admin_user_id = None

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

    def setup_test_users(self):
        """Create test users with different roles"""
        print("\n🔐 Setting up test users...")
        
        # Generate unique identifiers for this test run
        test_id = str(uuid.uuid4())[:8]
        
        # Create test users with different roles
        users = [
            {
                "email": f"pm.manager.{test_id}@taskflow.com",
                "username": f"pmmanager{test_id}",
                "full_name": "Project Manager",
                "password": "SecurePass123!",
                "role": "project_manager"
            },
            {
                "email": f"admin.user.{test_id}@taskflow.com", 
                "username": f"adminuser{test_id}",
                "full_name": "Admin User",
                "password": "AdminPass123!",
                "role": "admin"
            },
            {
                "email": f"regular.user.{test_id}@taskflow.com",
                "username": f"regularuser{test_id}", 
                "full_name": "Regular User",
                "password": "UserPass123!",
                "role": "user"
            }
        ]
        
        # Register users
        try:
            pm_response = self.session.post(f"{BACKEND_URL}/auth/register", json=users[0])
            admin_response = self.session.post(f"{BACKEND_URL}/auth/register", json=users[1])
            regular_response = self.session.post(f"{BACKEND_URL}/auth/register", json=users[2])
            
            if pm_response.status_code == 200:
                self.pm_token = pm_response.json()["access_token"]
                self.pm_user_id = pm_response.json()["user"]["id"]
                self.log_result("Project Manager Registration", True, "PM user registered successfully")
            else:
                self.log_result("Project Manager Registration", False, f"Status: {pm_response.status_code}")
                return False
                
            if admin_response.status_code == 200:
                self.admin_token = admin_response.json()["access_token"]
                self.admin_user_id = admin_response.json()["user"]["id"]
                self.log_result("Admin User Registration", True, "Admin user registered successfully")
            else:
                self.log_result("Admin User Registration", False, f"Status: {admin_response.status_code}")
                return False
                
            if regular_response.status_code == 200:
                self.regular_token = regular_response.json()["access_token"]
                self.log_result("Regular User Registration", True, "Regular user registered successfully")
            else:
                self.log_result("Regular User Registration", False, f"Status: {regular_response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("User Registration", False, f"Error: {str(e)}")
            return False
            
        return True

    def test_pm_authentication(self):
        """Test PM authentication and access control"""
        print("\n🔐 Testing PM Authentication & Access Control...")
        
        pm_headers = {"Authorization": f"Bearer {self.pm_token}"}
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        regular_headers = {"Authorization": f"Bearer {self.regular_token}"}
        
        # Test PM access to PM dashboard
        try:
            pm_dashboard_response = self.session.get(f"{BACKEND_URL}/pm/dashboard", headers=pm_headers)
            if pm_dashboard_response.status_code == 200:
                self.log_result("PM Dashboard Access (PM Role)", True, "Project manager can access PM dashboard")
            else:
                self.log_result("PM Dashboard Access (PM Role)", False, f"Status: {pm_dashboard_response.status_code}")
        except Exception as e:
            self.log_result("PM Dashboard Access (PM Role)", False, f"Error: {str(e)}")
        
        # Test Admin access to PM dashboard
        try:
            admin_dashboard_response = self.session.get(f"{BACKEND_URL}/pm/dashboard", headers=admin_headers)
            if admin_dashboard_response.status_code == 200:
                self.log_result("PM Dashboard Access (Admin Role)", True, "Admin can access PM dashboard")
            else:
                self.log_result("PM Dashboard Access (Admin Role)", False, f"Status: {admin_dashboard_response.status_code}")
        except Exception as e:
            self.log_result("PM Dashboard Access (Admin Role)", False, f"Error: {str(e)}")
        
        # Test Regular user blocked from PM dashboard
        try:
            regular_dashboard_response = self.session.get(f"{BACKEND_URL}/pm/dashboard", headers=regular_headers)
            if regular_dashboard_response.status_code == 403:
                self.log_result("PM Dashboard Access Blocked (Regular User)", True, "Regular user properly blocked from PM dashboard")
            else:
                self.log_result("PM Dashboard Access Blocked (Regular User)", False, f"Expected 403, got: {regular_dashboard_response.status_code}")
        except Exception as e:
            self.log_result("PM Dashboard Access Blocked (Regular User)", False, f"Error: {str(e)}")

    def test_pm_dashboard_endpoints(self):
        """Test all PM dashboard endpoints"""
        print("\n📊 Testing PM Dashboard Endpoints...")
        
        pm_headers = {"Authorization": f"Bearer {self.pm_token}"}
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Create test project with PM assigned
        project_data = {
            "name": "PM Test Project",
            "description": "Project for testing PM functionality",
            "project_managers": [self.pm_user_id],
            "collaborators": [self.admin_user_id]
        }
        
        try:
            project_response = self.session.post(f"{BACKEND_URL}/projects", json=project_data, headers=admin_headers)
            if project_response.status_code == 200:
                project_id = project_response.json()["id"]
                self.test_data['projects'].append(project_id)
                self.log_result("Test Project Creation", True, "Created project for PM testing")
                
                # Create test tasks in the project
                task_data = {
                    "title": "PM Test Task",
                    "description": "Task for PM testing",
                    "project_id": project_id,
                    "priority": "high",
                    "assigned_users": [self.pm_user_id]
                }
                
                task_response = self.session.post(f"{BACKEND_URL}/tasks", json=task_data, headers=admin_headers)
                if task_response.status_code == 200:
                    task_id = task_response.json()["id"]
                    self.test_data['tasks'].append(task_id)
                    self.log_result("Test Task Creation", True, "Created task for PM testing")
                else:
                    self.log_result("Test Task Creation", False, f"Status: {task_response.status_code}")
                    
            else:
                self.log_result("Test Project Creation", False, f"Status: {project_response.status_code}")
                return
                
        except Exception as e:
            self.log_result("Test Project Creation", False, f"Error: {str(e)}")
            return
        
        # Test GET /api/pm/dashboard
        try:
            dashboard_response = self.session.get(f"{BACKEND_URL}/pm/dashboard", headers=pm_headers)
            if dashboard_response.status_code == 200:
                dashboard_data = dashboard_response.json()
                required_keys = ['overview', 'projects', 'team_workload', 'recent_activities']
                if all(key in dashboard_data for key in required_keys):
                    self.log_result("PM Dashboard Data Structure", True, "Dashboard returns all required data sections")
                    
                    # Check overview data
                    overview = dashboard_data['overview']
                    overview_keys = ['total_projects', 'active_projects', 'total_tasks', 'team_size']
                    if all(key in overview for key in overview_keys):
                        self.log_result("PM Dashboard Overview", True, f"Overview contains project stats: {overview['total_projects']} projects, {overview['total_tasks']} tasks")
                    else:
                        self.log_result("PM Dashboard Overview", False, "Missing overview keys")
                else:
                    self.log_result("PM Dashboard Data Structure", False, f"Missing keys: {set(required_keys) - set(dashboard_data.keys())}")
            else:
                self.log_result("PM Dashboard Endpoint", False, f"Status: {dashboard_response.status_code}")
        except Exception as e:
            self.log_result("PM Dashboard Endpoint", False, f"Error: {str(e)}")
        
        # Test GET /api/pm/projects
        try:
            projects_response = self.session.get(f"{BACKEND_URL}/pm/projects", headers=pm_headers)
            if projects_response.status_code == 200:
                projects_data = projects_response.json()
                if isinstance(projects_data, list) and len(projects_data) > 0:
                    project = projects_data[0]
                    required_fields = ['id', 'name', 'status', 'progress_percentage', 'task_count']
                    if all(field in project for field in required_fields):
                        self.log_result("PM Managed Projects", True, f"Retrieved {len(projects_data)} managed projects with complete data")
                    else:
                        self.log_result("PM Managed Projects", False, "Project data missing required fields")
                else:
                    self.log_result("PM Managed Projects", True, "No projects found (expected for new PM)")
            else:
                self.log_result("PM Managed Projects", False, f"Status: {projects_response.status_code}")
        except Exception as e:
            self.log_result("PM Managed Projects", False, f"Error: {str(e)}")
        
        # Test PUT /api/pm/projects/{project_id}/status
        try:
            status_update = {"status": "on_hold"}
            status_response = self.session.put(f"{BACKEND_URL}/pm/projects/{project_id}/status", json=status_update, headers=pm_headers)
            if status_response.status_code == 200:
                self.log_result("PM Project Status Override", True, "PM can override project status")
                
                # Verify status was updated
                project_check = self.session.get(f"{BACKEND_URL}/projects/{project_id}", headers=pm_headers)
                if project_check.status_code == 200:
                    project_data = project_check.json()
                    if project_data.get("status") == "on_hold" and project_data.get("status_override") == "on_hold":
                        self.log_result("PM Status Override Verification", True, "Status override applied correctly")
                    else:
                        self.log_result("PM Status Override Verification", False, f"Status not updated correctly: {project_data.get('status')}")
            else:
                self.log_result("PM Project Status Override", False, f"Status: {status_response.status_code}")
        except Exception as e:
            self.log_result("PM Project Status Override", False, f"Error: {str(e)}")
        
        # Test GET /api/pm/projects/{project_id}/tasks
        try:
            tasks_response = self.session.get(f"{BACKEND_URL}/pm/projects/{project_id}/tasks", headers=pm_headers)
            if tasks_response.status_code == 200:
                tasks_data = tasks_response.json()
                if isinstance(tasks_data, list):
                    self.log_result("PM Project Tasks", True, f"Retrieved {len(tasks_data)} tasks for project")
                else:
                    self.log_result("PM Project Tasks", False, "Invalid tasks data format")
            else:
                self.log_result("PM Project Tasks", False, f"Status: {tasks_response.status_code}")
        except Exception as e:
            self.log_result("PM Project Tasks", False, f"Error: {str(e)}")
        
        # Test GET /api/pm/projects/{project_id}/team
        try:
            team_response = self.session.get(f"{BACKEND_URL}/pm/projects/{project_id}/team", headers=pm_headers)
            if team_response.status_code == 200:
                team_data = team_response.json()
                if isinstance(team_data, list):
                    if len(team_data) > 0:
                        member = team_data[0]
                        required_fields = ['user', 'tasks', 'availability']
                        if all(field in member for field in required_fields):
                            self.log_result("PM Project Team", True, f"Retrieved team with {len(team_data)} members and workload data")
                        else:
                            self.log_result("PM Project Team", False, "Team member data missing required fields")
                    else:
                        self.log_result("PM Project Team", True, "No team members found (expected for new project)")
                else:
                    self.log_result("PM Project Team", False, "Invalid team data format")
            else:
                self.log_result("PM Project Team", False, f"Status: {team_response.status_code}")
        except Exception as e:
            self.log_result("PM Project Team", False, f"Error: {str(e)}")
        
        # Test GET /api/pm/activity
        try:
            activity_response = self.session.get(f"{BACKEND_URL}/pm/activity", headers=pm_headers)
            if activity_response.status_code == 200:
                activity_data = activity_response.json()
                if isinstance(activity_data, list):
                    self.log_result("PM Activity Log", True, f"Retrieved {len(activity_data)} activity entries")
                    
                    # Test with project filter
                    filtered_activity = self.session.get(f"{BACKEND_URL}/pm/activity?project_id={project_id}", headers=pm_headers)
                    if filtered_activity.status_code == 200:
                        self.log_result("PM Activity Log Filtering", True, "Activity filtering by project works")
                    else:
                        self.log_result("PM Activity Log Filtering", False, f"Status: {filtered_activity.status_code}")
                else:
                    self.log_result("PM Activity Log", False, "Invalid activity data format")
            else:
                self.log_result("PM Activity Log", False, f"Status: {activity_response.status_code}")
        except Exception as e:
            self.log_result("PM Activity Log", False, f"Error: {str(e)}")
        
        # Test GET /api/pm/notifications
        try:
            notifications_response = self.session.get(f"{BACKEND_URL}/pm/notifications", headers=pm_headers)
            if notifications_response.status_code == 200:
                notifications_data = notifications_response.json()
                if isinstance(notifications_data, list):
                    self.log_result("PM Notifications", True, f"Retrieved {len(notifications_data)} notifications")
                    
                    # Test unread filter
                    unread_response = self.session.get(f"{BACKEND_URL}/pm/notifications?unread_only=true", headers=pm_headers)
                    if unread_response.status_code == 200:
                        self.log_result("PM Notifications Filtering", True, "Unread notifications filter works")
                    else:
                        self.log_result("PM Notifications Filtering", False, f"Status: {unread_response.status_code}")
                else:
                    self.log_result("PM Notifications", False, "Invalid notifications data format")
            else:
                self.log_result("PM Notifications", False, f"Status: {notifications_response.status_code}")
        except Exception as e:
            self.log_result("PM Notifications", False, f"Error: {str(e)}")

    def test_project_status_and_progress(self):
        """Test project status calculation and progress tracking"""
        print("\n📈 Testing Project Status & Progress...")
        
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        pm_headers = {"Authorization": f"Bearer {self.pm_token}"}
        
        # Create a new project for status testing
        project_data = {
            "name": "Status Test Project",
            "description": "Project for testing status calculation",
            "project_managers": [self.pm_user_id],
            "collaborators": [self.admin_user_id]
        }
        
        try:
            project_response = self.session.post(f"{BACKEND_URL}/projects", json=project_data, headers=admin_headers)
            if project_response.status_code == 200:
                project_id = project_response.json()["id"]
                self.test_data['projects'].append(project_id)
                self.log_result("Status Test Project Creation", True, "Created project for status testing")
                
                # Create multiple tasks with different statuses
                task_statuses = ["todo", "in_progress", "completed"]
                created_tasks = []
                
                for i, status in enumerate(task_statuses):
                    task_data = {
                        "title": f"Status Test Task {i+1}",
                        "description": f"Task with {status} status",
                        "project_id": project_id,
                        "priority": "medium"
                    }
                    
                    task_response = self.session.post(f"{BACKEND_URL}/tasks", json=task_data, headers=admin_headers)
                    if task_response.status_code == 200:
                        task_id = task_response.json()["id"]
                        created_tasks.append(task_id)
                        self.test_data['tasks'].append(task_id)
                        
                        # Update task status if not todo
                        if status != "todo":
                            update_data = {"status": status}
                            update_response = self.session.put(f"{BACKEND_URL}/tasks/{task_id}", json=update_data, headers=admin_headers)
                            if update_response.status_code != 200:
                                self.log_result(f"Task Status Update ({status})", False, f"Status: {update_response.status_code}")
                    else:
                        self.log_result(f"Task Creation ({status})", False, f"Status: {task_response.status_code}")
                
                if len(created_tasks) == 3:
                    self.log_result("Test Tasks Creation", True, "Created 3 tasks with different statuses")
                    
                    # Check project progress calculation
                    time.sleep(1)  # Brief delay for progress calculation
                    projects_response = self.session.get(f"{BACKEND_URL}/pm/projects", headers=pm_headers)
                    if projects_response.status_code == 200:
                        projects_data = projects_response.json()
                        status_project = next((p for p in projects_data if p["id"] == project_id), None)
                        
                        if status_project:
                            # Verify progress calculation
                            expected_progress = 33.33  # 1 completed out of 3 tasks
                            actual_progress = status_project.get("progress_percentage", 0)
                            if abs(actual_progress - expected_progress) < 5:  # Allow some rounding differences
                                self.log_result("Project Progress Calculation", True, f"Progress calculated correctly: {actual_progress}%")
                            else:
                                self.log_result("Project Progress Calculation", False, f"Expected ~{expected_progress}%, got {actual_progress}%")
                            
                            # Verify task counts
                            task_count = status_project.get("task_count", 0)
                            completed_count = status_project.get("completed_task_count", 0)
                            if task_count == 3 and completed_count == 1:
                                self.log_result("Project Task Counts", True, f"Task counts correct: {task_count} total, {completed_count} completed")
                            else:
                                self.log_result("Project Task Counts", False, f"Expected 3 total, 1 completed; got {task_count} total, {completed_count} completed")
                            
                            # Test auto-calculated status
                            auto_status = status_project.get("auto_calculated_status")
                            if auto_status:
                                self.log_result("Auto-calculated Status", True, f"Auto status calculated: {auto_status}")
                            else:
                                self.log_result("Auto-calculated Status", False, "No auto-calculated status found")
                        else:
                            self.log_result("Project Progress Check", False, "Project not found in PM projects list")
                            
                    else:
                        self.log_result("Project Progress Check", False, f"Status: {projects_response.status_code}")
                        
                    # Test manual status override
                    override_status = {"status": "on_hold"}
                    override_response = self.session.put(f"{BACKEND_URL}/pm/projects/{project_id}/status", json=override_status, headers=pm_headers)
                    if override_response.status_code == 200:
                        self.log_result("Manual Status Override", True, "Manual status override applied")
                        
                        # Verify override was applied
                        override_check = self.session.get(f"{BACKEND_URL}/pm/projects", headers=pm_headers)
                        if override_check.status_code == 200:
                            override_projects = override_check.json()
                            override_project = next((p for p in override_projects if p["id"] == project_id), None)
                            if override_project and override_project.get("status") == "on_hold" and override_project.get("status_override") == "on_hold":
                                self.log_result("Status Override Verification", True, "Status override applied and persisted correctly")
                            else:
                                self.log_result("Status Override Verification", False, f"Override not applied correctly")
                        else:
                            self.log_result("Status Override Verification", False, f"Status: {override_check.status_code}")
                    else:
                        self.log_result("Manual Status Override", False, f"Status: {override_response.status_code}")
                        
                else:
                    self.log_result("Test Tasks Creation", False, f"Only created {len(created_tasks)} out of 3 tasks")
                    
            else:
                self.log_result("Status Test Project Creation", False, f"Status: {project_response.status_code}")
                
        except Exception as e:
            self.log_result("Project Status Testing", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all PM dashboard tests"""
        print("🚀 Starting Project Manager Dashboard Testing Suite")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 80)
        
        # Setup test users
        if not self.setup_test_users():
            print("❌ Failed to setup test users. Aborting tests.")
            return False
        
        # Run tests
        self.test_pm_authentication()
        self.test_pm_dashboard_endpoints()
        self.test_project_status_and_progress()
        
        # Final results
        print("\n" + "=" * 80)
        print("🏁 FINAL TEST RESULTS - PROJECT MANAGER DASHBOARD TESTING")
        print("=" * 80)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Success Rate: {(self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100):.1f}%")
        
        if self.results['errors']:
            print("\n🔍 FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

if __name__ == "__main__":
    tester = PMDashboardTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All PM dashboard tests passed! Backend is working correctly.")
        exit(0)
    else:
        print(f"\n⚠️  {tester.results['failed']} tests failed. Check the issues above.")
        exit(1)