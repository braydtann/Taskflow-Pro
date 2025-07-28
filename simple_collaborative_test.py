#!/usr/bin/env python3
"""
Simplified Collaborative Features Test - Focus on working functionality
Tests the collaborative features that are implemented and working
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
import time

# Configuration
BACKEND_URL = "https://9b427bd1-3e37-401f-bf28-80af2a6bf86c.preview.emergentagent.com/api"
TIMEOUT = 30

class SimpleCollaborativeTest:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = TIMEOUT
        self.test_data = {
            'admin_user': None,
            'users': [],
            'teams': [],
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

    def setup_test_users(self):
        """Setup test users"""
        print("\n=== Setting Up Test Users ===")
        
        try:
            # Login as admin
            admin_data = {"email": "admin@taskflow.com", "password": "AdminPassword123"}
            response = self.session.post(f"{BACKEND_URL}/auth/login", json=admin_data)
            if response.status_code == 200:
                admin_result = response.json()
                self.test_data['admin_user'] = admin_result['user']
                self.test_data['tokens']['admin'] = admin_result['access_token']
                self.log_result("Admin Login", True, f"Admin logged in: {admin_result['user']['email']}")
            else:
                self.log_result("Admin Login", False, f"HTTP {response.status_code}")
                return False

            # Create new test users with unique emails
            test_users = [
                {
                    "email": f"testuser1_{int(time.time())}@example.com",
                    "username": f"testuser1_{int(time.time())}",
                    "full_name": "Test User 1",
                    "password": "TestPassword123"
                },
                {
                    "email": f"testuser2_{int(time.time())}@example.com",
                    "username": f"testuser2_{int(time.time())}",
                    "full_name": "Test User 2", 
                    "password": "TestPassword123"
                }
            ]
            
            for user_data in test_users:
                response = self.session.post(f"{BACKEND_URL}/auth/register", json=user_data)
                if response.status_code == 200:
                    user_result = response.json()
                    self.test_data['users'].append(user_result['user'])
                    self.test_data['tokens'][user_result['user']['username']] = user_result['access_token']
                    self.log_result(f"User Registration - {user_data['username']}", True, f"User created: {user_result['user']['email']}")
                else:
                    self.log_result(f"User Registration - {user_data['username']}", False, f"HTTP {response.status_code}: {response.text}")
            
            return len(self.test_data['users']) >= 2
            
        except Exception as e:
            self.log_result("User Setup", False, f"Error: {str(e)}")
            return False

    def test_team_management(self):
        """Test team management functionality"""
        print("\n=== Testing Team Management ===")
        
        if not self.test_data['admin_user'] or len(self.test_data['users']) < 2:
            self.log_result("Team Management Setup", False, "Admin or users not available")
            return False
        
        try:
            admin_token = self.test_data['tokens']['admin']
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Create team with test users
            team_data = {
                "name": f"Test Team {int(time.time())}",
                "description": "Test team for collaborative features",
                "team_lead_id": self.test_data['users'][0]['id'],
                "members": [user['id'] for user in self.test_data['users']]
            }
            
            response = self.session.post(f"{BACKEND_URL}/admin/teams", json=team_data, headers=headers)
            if response.status_code == 200:
                team = response.json()
                self.test_data['teams'].append(team)
                self.log_result("Create Team", True, f"Team created: {team['name']} with {len(team['members'])} members")
                return True
            else:
                self.log_result("Create Team", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Team Management", False, f"Error: {str(e)}")
            return False

    def test_collaborative_project(self):
        """Test collaborative project creation"""
        print("\n=== Testing Collaborative Project ===")
        
        if len(self.test_data['users']) < 2:
            self.log_result("Collaborative Project Setup", False, "Insufficient users")
            return False
        
        try:
            user1_token = self.test_data['tokens'][self.test_data['users'][0]['username']]
            headers = {"Authorization": f"Bearer {user1_token}"}
            
            # Create project with collaborators
            project_data = {
                "name": f"Collaborative Project {int(time.time())}",
                "description": "Test project for collaborative features",
                "collaborators": [self.test_data['users'][1]['id']],
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
            }
            
            response = self.session.post(f"{BACKEND_URL}/projects", json=project_data, headers=headers)
            if response.status_code == 200:
                project = response.json()
                self.test_data['projects'].append(project)
                self.log_result("Create Collaborative Project", True, f"Project created with {len(project['collaborators'])} collaborators")
                
                # Test collaborator access
                user2_token = self.test_data['tokens'][self.test_data['users'][1]['username']]
                user2_headers = {"Authorization": f"Bearer {user2_token}"}
                
                response = self.session.get(f"{BACKEND_URL}/projects/{project['id']}", headers=user2_headers)
                if response.status_code == 200:
                    self.log_result("Collaborator Project Access", True, "Collaborator can access project")
                else:
                    self.log_result("Collaborator Project Access", False, f"HTTP {response.status_code}")
                
                return True
            else:
                self.log_result("Create Collaborative Project", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Collaborative Project", False, f"Error: {str(e)}")
            return False

    def test_collaborative_tasks(self):
        """Test collaborative task creation and access"""
        print("\n=== Testing Collaborative Tasks ===")
        
        if not self.test_data['projects'] or len(self.test_data['users']) < 2:
            self.log_result("Collaborative Tasks Setup", False, "Projects or users not available")
            return False
        
        try:
            project = self.test_data['projects'][0]
            user1_token = self.test_data['tokens'][self.test_data['users'][0]['username']]
            headers = {"Authorization": f"Bearer {user1_token}"}
            
            # Create task with assigned users and collaborators
            task_data = {
                "title": f"Collaborative Task {int(time.time())}",
                "description": "Test task for collaborative features",
                "priority": "high",
                "project_id": project['id'],
                "estimated_duration": 240,
                "due_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
                "assigned_users": [self.test_data['users'][1]['id']],
                "collaborators": [self.test_data['users'][1]['id']],
                "tags": ["collaboration", "test"]
            }
            
            response = self.session.post(f"{BACKEND_URL}/tasks", json=task_data, headers=headers)
            if response.status_code == 200:
                task = response.json()
                self.test_data['tasks'].append(task)
                self.log_result("Create Collaborative Task", True, f"Task created with {len(task['assigned_users'])} assigned users")
                
                # Test assigned user access
                user2_token = self.test_data['tokens'][self.test_data['users'][1]['username']]
                user2_headers = {"Authorization": f"Bearer {user2_token}"}
                
                response = self.session.get(f"{BACKEND_URL}/tasks/{task['id']}", headers=user2_headers)
                if response.status_code == 200:
                    self.log_result("Assigned User Task Access", True, "Assigned user can access task")
                else:
                    self.log_result("Assigned User Task Access", False, f"HTTP {response.status_code}")
                
                # Test task update by assigned user
                update_data = {"status": "in_progress", "description": "Updated by assigned user"}
                response = self.session.put(f"{BACKEND_URL}/tasks/{task['id']}", json=update_data, headers=user2_headers)
                if response.status_code == 200:
                    self.log_result("Assigned User Can Update", True, "Assigned user can update task")
                else:
                    self.log_result("Assigned User Can Update", False, f"HTTP {response.status_code}")
                
                return True
            else:
                self.log_result("Create Collaborative Task", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Collaborative Tasks", False, f"Error: {str(e)}")
            return False

    def test_multi_user_data_access(self):
        """Test multi-user data access and isolation"""
        print("\n=== Testing Multi-user Data Access ===")
        
        if len(self.test_data['users']) < 2:
            self.log_result("Multi-user Access Setup", False, "Insufficient users")
            return False
        
        try:
            # Test that each user sees appropriate data
            for i, user in enumerate(self.test_data['users']):
                user_token = self.test_data['tokens'][user['username']]
                headers = {"Authorization": f"Bearer {user_token}"}
                
                # Get user's tasks
                response = self.session.get(f"{BACKEND_URL}/tasks", headers=headers)
                if response.status_code == 200:
                    user_tasks = response.json()
                    self.log_result(f"User {i+1} Task Access", True, f"User sees {len(user_tasks)} tasks")
                    
                    # Verify user can only see appropriate tasks
                    for task in user_tasks:
                        if not (task.get('owner_id') == user['id'] or 
                               user['id'] in task.get('assigned_users', []) or 
                               user['id'] in task.get('collaborators', [])):
                            self.log_result(f"User {i+1} Data Isolation", False, "User sees unauthorized task")
                            break
                    else:
                        self.log_result(f"User {i+1} Data Isolation", True, "User only sees authorized tasks")
                else:
                    self.log_result(f"User {i+1} Task Access", False, f"HTTP {response.status_code}")
                
                # Get user's projects
                response = self.session.get(f"{BACKEND_URL}/projects", headers=headers)
                if response.status_code == 200:
                    user_projects = response.json()
                    self.log_result(f"User {i+1} Project Access", True, f"User sees {len(user_projects)} projects")
                else:
                    self.log_result(f"User {i+1} Project Access", False, f"HTTP {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log_result("Multi-user Data Access", False, f"Error: {str(e)}")
            return False

    def test_websocket_endpoint_availability(self):
        """Test if WebSocket endpoint is available (basic connectivity)"""
        print("\n=== Testing WebSocket Endpoint Availability ===")
        
        try:
            # Test if WebSocket endpoint responds (even if it rejects the connection)
            import socket
            import ssl
            
            # Parse WebSocket URL
            ws_host = "5f9f27c3-39df-42c0-9993-777740083949.preview.emergentagent.com"
            ws_port = 443
            
            # Test basic connectivity
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            try:
                # Wrap with SSL for wss://
                context = ssl.create_default_context()
                ssl_sock = context.wrap_socket(sock, server_hostname=ws_host)
                result = ssl_sock.connect_ex((ws_host, ws_port))
                ssl_sock.close()
                
                if result == 0:
                    self.log_result("WebSocket Endpoint Connectivity", True, "WebSocket endpoint is reachable")
                else:
                    self.log_result("WebSocket Endpoint Connectivity", False, f"Connection failed: {result}")
            except Exception as e:
                self.log_result("WebSocket Endpoint Connectivity", False, f"Connection error: {str(e)}")
            finally:
                sock.close()
            
            return True
            
        except Exception as e:
            self.log_result("WebSocket Endpoint Availability", False, f"Error: {str(e)}")
            return False

    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n=== Cleaning Up Test Data ===")
        
        try:
            # Delete test tasks
            if self.test_data['tasks'] and self.test_data['users']:
                user1_token = self.test_data['tokens'][self.test_data['users'][0]['username']]
                headers = {"Authorization": f"Bearer {user1_token}"}
                
                for task in self.test_data['tasks']:
                    try:
                        response = self.session.delete(f"{BACKEND_URL}/tasks/{task['id']}", headers=headers)
                        if response.status_code == 200:
                            print(f"✅ Deleted task: {task['title']}")
                        else:
                            print(f"❌ Failed to delete task: {task['title']}")
                    except Exception as e:
                        print(f"❌ Error deleting task {task['title']}: {str(e)}")
            
            # Delete test teams
            if self.test_data['teams'] and self.test_data['admin_user']:
                admin_token = self.test_data['tokens']['admin']
                headers = {"Authorization": f"Bearer {admin_token}"}
                
                for team in self.test_data['teams']:
                    try:
                        response = self.session.delete(f"{BACKEND_URL}/admin/teams/{team['id']}", headers=headers)
                        if response.status_code == 200:
                            print(f"✅ Deleted team: {team['name']}")
                        else:
                            print(f"❌ Failed to delete team: {team['name']}")
                    except Exception as e:
                        print(f"❌ Error deleting team {team['name']}: {str(e)}")
            
            print("Cleanup completed")
            
        except Exception as e:
            print(f"❌ Cleanup error: {str(e)}")

    def run_all_tests(self):
        """Run all collaborative features tests"""
        print("🚀 Starting Simplified Collaborative Features Testing")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 60)
        
        # Test sequence
        tests = [
            self.setup_test_users,
            self.test_team_management,
            self.test_collaborative_project,
            self.test_collaborative_tasks,
            self.test_multi_user_data_access,
            self.test_websocket_endpoint_availability
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
        print("\n" + "=" * 60)
        print("🏁 COLLABORATIVE FEATURES TEST RESULTS")
        print("=" * 60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Success Rate: {(self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100):.1f}%")
        
        if self.results['errors']:
            print("\n🔍 FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

if __name__ == "__main__":
    tester = SimpleCollaborativeTest()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All collaborative features tests passed!")
        exit(0)
    else:
        print(f"\n⚠️  {tester.results['failed']} tests failed.")
        exit(1)