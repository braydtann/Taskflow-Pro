#!/usr/bin/env python3
"""
Comprehensive Real-time Collaborative Features Test
Tests all collaborative features including WebSocket real-time updates
"""

import requests
import json
import uuid
import asyncio
import websockets
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Configuration
BACKEND_URL = "https://c8100f3d-9630-4d28-8ec8-815398f88ad4.preview.emergentagent.com/api"
WEBSOCKET_URL = "wss://5f9f27c3-39df-42c0-9993-777740083949.preview.emergentagent.com/ws"
TIMEOUT = 30

class ComprehensiveCollaborativeTest:
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
        self.websocket_messages = []

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
            timestamp = int(time.time())
            test_users = [
                {
                    "email": f"rtuser1_{timestamp}@example.com",
                    "username": f"rtuser1_{timestamp}",
                    "full_name": "Real-time User 1",
                    "password": "RealTimePass123"
                },
                {
                    "email": f"rtuser2_{timestamp}@example.com",
                    "username": f"rtuser2_{timestamp}",
                    "full_name": "Real-time User 2", 
                    "password": "RealTimePass123"
                },
                {
                    "email": f"rtuser3_{timestamp}@example.com",
                    "username": f"rtuser3_{timestamp}",
                    "full_name": "Real-time User 3", 
                    "password": "RealTimePass123"
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
            
            return len(self.test_data['users']) >= 3
            
        except Exception as e:
            self.log_result("User Setup", False, f"Error: {str(e)}")
            return False

    def test_team_management_comprehensive(self):
        """Test comprehensive team management"""
        print("\n=== Testing Comprehensive Team Management ===")
        
        if not self.test_data['admin_user'] or len(self.test_data['users']) < 3:
            self.log_result("Team Management Setup", False, "Admin or users not available")
            return False
        
        try:
            admin_token = self.test_data['tokens']['admin']
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Create team with multiple users
            team_data = {
                "name": f"Real-time Collaboration Team {int(time.time())}",
                "description": "Team for testing real-time collaborative features",
                "team_lead_id": self.test_data['users'][0]['id'],
                "members": [user['id'] for user in self.test_data['users']]
            }
            
            response = self.session.post(f"{BACKEND_URL}/admin/teams", json=team_data, headers=headers)
            if response.status_code == 200:
                team = response.json()
                self.test_data['teams'].append(team)
                self.log_result("Create Team", True, f"Team created: {team['name']} with {len(team['members'])} members")
                
                # Test team member assignment
                for i, user in enumerate(self.test_data['users']):
                    user_token = self.test_data['tokens'][user['username']]
                    user_headers = {"Authorization": f"Bearer {user_token}"}
                    
                    # Check if user can see team-related data (this would be through projects/tasks)
                    response = self.session.get(f"{BACKEND_URL}/projects", headers=user_headers)
                    if response.status_code == 200:
                        self.log_result(f"Team Member {i+1} Access", True, f"Team member can access system")
                    else:
                        self.log_result(f"Team Member {i+1} Access", False, f"HTTP {response.status_code}")
                
                return True
            else:
                self.log_result("Create Team", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Team Management", False, f"Error: {str(e)}")
            return False

    def test_project_team_integration(self):
        """Test project-team integration"""
        print("\n=== Testing Project-Team Integration ===")
        
        if len(self.test_data['users']) < 3:
            self.log_result("Project-Team Integration Setup", False, "Insufficient users")
            return False
        
        try:
            user1_token = self.test_data['tokens'][self.test_data['users'][0]['username']]
            headers = {"Authorization": f"Bearer {user1_token}"}
            
            # Create project with multiple collaborators
            project_data = {
                "name": f"Real-time Collaborative Project {int(time.time())}",
                "description": "Project for testing real-time collaborative features",
                "collaborators": [user['id'] for user in self.test_data['users'][1:3]],
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
            }
            
            response = self.session.post(f"{BACKEND_URL}/projects", json=project_data, headers=headers)
            if response.status_code == 200:
                project = response.json()
                self.test_data['projects'].append(project)
                self.log_result("Create Team Project", True, f"Project created with {len(project['collaborators'])} collaborators")
                
                # Test all collaborators can access project
                for i, user in enumerate(self.test_data['users'][1:3]):
                    user_token = self.test_data['tokens'][user['username']]
                    user_headers = {"Authorization": f"Bearer {user_token}"}
                    
                    response = self.session.get(f"{BACKEND_URL}/projects/{project['id']}", headers=user_headers)
                    if response.status_code == 200:
                        self.log_result(f"Collaborator {i+1} Project Access", True, "Collaborator can access project")
                    else:
                        self.log_result(f"Collaborator {i+1} Project Access", False, f"HTTP {response.status_code}")
                
                return True
            else:
                self.log_result("Create Team Project", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Project-Team Integration", False, f"Error: {str(e)}")
            return False

    def test_collaborative_task_creation(self):
        """Test collaborative task creation with multiple users"""
        print("\n=== Testing Collaborative Task Creation ===")
        
        if not self.test_data['projects'] or len(self.test_data['users']) < 3:
            self.log_result("Collaborative Task Setup", False, "Projects or users not available")
            return False
        
        try:
            project = self.test_data['projects'][0]
            user1_token = self.test_data['tokens'][self.test_data['users'][0]['username']]
            headers = {"Authorization": f"Bearer {user1_token}"}
            
            # Create task with multiple assigned users and collaborators
            task_data = {
                "title": f"Real-time Collaborative Task {int(time.time())}",
                "description": "Task for testing real-time collaborative features",
                "priority": "high",
                "project_id": project['id'],
                "estimated_duration": 480,
                "due_date": (datetime.utcnow() + timedelta(days=5)).isoformat(),
                "assigned_users": [self.test_data['users'][1]['id'], self.test_data['users'][2]['id']],
                "collaborators": [self.test_data['users'][2]['id']],
                "tags": ["real-time", "collaboration", "websocket"]
            }
            
            response = self.session.post(f"{BACKEND_URL}/tasks", json=task_data, headers=headers)
            if response.status_code == 200:
                task = response.json()
                self.test_data['tasks'].append(task)
                self.log_result("Create Multi-user Task", True, f"Task created with {len(task['assigned_users'])} assigned users and {len(task['collaborators'])} collaborators")
                
                # Test all assigned users can access task
                for i, user in enumerate(self.test_data['users'][1:3]):
                    user_token = self.test_data['tokens'][user['username']]
                    user_headers = {"Authorization": f"Bearer {user_token}"}
                    
                    response = self.session.get(f"{BACKEND_URL}/tasks/{task['id']}", headers=user_headers)
                    if response.status_code == 200:
                        self.log_result(f"Assigned User {i+1} Task Access", True, "Assigned user can access task")
                    else:
                        self.log_result(f"Assigned User {i+1} Task Access", False, f"HTTP {response.status_code}")
                
                return True
            else:
                self.log_result("Create Multi-user Task", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Collaborative Task Creation", False, f"Error: {str(e)}")
            return False

    def test_websocket_authentication(self):
        """Test WebSocket authentication with JWT"""
        print("\n=== Testing WebSocket Authentication ===")
        
        if len(self.test_data['users']) < 1:
            self.log_result("WebSocket Auth Setup", False, "Users not available")
            return False
        
        try:
            user = self.test_data['users'][0]
            token = self.test_data['tokens'][user['username']]
            
            async def test_websocket_auth():
                try:
                    uri = f"{WEBSOCKET_URL}/{user['id']}?token={token}"
                    async with websockets.connect(uri) as websocket:
                        # Wait for welcome message
                        message = await asyncio.wait_for(websocket.recv(), timeout=10)
                        data = json.loads(message)
                        
                        if data.get('type') == 'connection_established':
                            return True, "WebSocket authentication successful"
                        else:
                            return False, f"Unexpected message: {data}"
                            
                except asyncio.TimeoutError:
                    return False, "WebSocket connection timeout"
                except websockets.exceptions.ConnectionClosedError as e:
                    return False, f"Connection closed: {e.code} - {e.reason}"
                except Exception as e:
                    return False, f"WebSocket error: {str(e)}"
            
            # Run async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success, message = loop.run_until_complete(test_websocket_auth())
                self.log_result("WebSocket JWT Authentication", success, message)
                return success
            finally:
                loop.close()
                
        except Exception as e:
            self.log_result("WebSocket Authentication", False, f"Error: {str(e)}")
            return False

    def test_real_time_task_updates(self):
        """Test real-time task updates via WebSocket"""
        print("\n=== Testing Real-time Task Updates ===")
        
        if not self.test_data['tasks'] or len(self.test_data['users']) < 2:
            self.log_result("Real-time Updates Setup", False, "Tasks or users not available")
            return False
        
        try:
            task = self.test_data['tasks'][0]
            owner = self.test_data['users'][0]
            collaborator = self.test_data['users'][1]
            
            owner_token = self.test_data['tokens'][owner['username']]
            collab_token = self.test_data['tokens'][collaborator['username']]
            
            received_updates = []
            
            async def test_real_time():
                try:
                    # Connect collaborator to WebSocket
                    uri = f"{WEBSOCKET_URL}/{collaborator['id']}?token={collab_token}"
                    async with websockets.connect(uri) as websocket:
                        # Skip welcome message
                        welcome = await asyncio.wait_for(websocket.recv(), timeout=5)
                        
                        # Set up listener task
                        async def listen_for_updates():
                            try:
                                while True:
                                    message = await asyncio.wait_for(websocket.recv(), timeout=15)
                                    data = json.loads(message)
                                    if data.get('type') == 'task_update':
                                        received_updates.append(data)
                                        break
                            except asyncio.TimeoutError:
                                pass
                        
                        # Start listening
                        listener_task = asyncio.create_task(listen_for_updates())
                        
                        # Wait a moment for connection to stabilize
                        await asyncio.sleep(2)
                        
                        # Update task via REST API (this should trigger WebSocket broadcast)
                        update_data = {
                            "status": "in_progress",
                            "description": "Updated for real-time testing - WebSocket broadcast test"
                        }
                        
                        headers = {"Authorization": f"Bearer {owner_token}"}
                        response = requests.put(f"{BACKEND_URL}/tasks/{task['id']}", json=update_data, headers=headers)
                        
                        if response.status_code == 200:
                            # Wait for WebSocket update
                            await asyncio.wait_for(listener_task, timeout=10)
                            
                            if received_updates:
                                update = received_updates[0]
                                if (update.get('action') == 'updated' and 
                                    update.get('task', {}).get('id') == task['id']):
                                    return True, f"Received real-time update: {update['action']}"
                                else:
                                    return False, f"Invalid update content: {update}"
                            else:
                                return False, "No real-time update received"
                        else:
                            return False, f"Task update failed: HTTP {response.status_code}"
                            
                except asyncio.TimeoutError:
                    return False, "Real-time update timeout"
                except Exception as e:
                    return False, f"Real-time test error: {str(e)}"
            
            # Run async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success, message = loop.run_until_complete(test_real_time())
                self.log_result("Real-time Task Updates", success, message)
                return success
            finally:
                loop.close()
                
        except Exception as e:
            self.log_result("Real-time Task Updates", False, f"Error: {str(e)}")
            return False

    def test_multi_user_collaboration(self):
        """Test multi-user collaboration scenarios"""
        print("\n=== Testing Multi-user Collaboration ===")
        
        if not self.test_data['tasks'] or len(self.test_data['users']) < 3:
            self.log_result("Multi-user Collaboration Setup", False, "Tasks or users not available")
            return False
        
        try:
            task = self.test_data['tasks'][0]
            
            # Test that multiple users can update the same task
            for i, user in enumerate(self.test_data['users'][:3]):
                user_token = self.test_data['tokens'][user['username']]
                headers = {"Authorization": f"Bearer {user_token}"}
                
                # Each user updates different aspects of the task
                if i == 0:  # Owner
                    update_data = {"priority": "urgent", "description": f"Updated by owner {user['username']}"}
                elif i == 1:  # Assigned user
                    update_data = {"status": "in_progress", "description": f"Updated by assigned user {user['username']}"}
                else:  # Collaborator
                    update_data = {"description": f"Updated by collaborator {user['username']}"}
                
                response = self.session.put(f"{BACKEND_URL}/tasks/{task['id']}", json=update_data, headers=headers)
                if response.status_code == 200:
                    self.log_result(f"User {i+1} Task Update", True, f"User {user['username']} can update task")
                else:
                    self.log_result(f"User {i+1} Task Update", False, f"HTTP {response.status_code}")
            
            # Test task visibility across all users
            for i, user in enumerate(self.test_data['users'][:3]):
                user_token = self.test_data['tokens'][user['username']]
                headers = {"Authorization": f"Bearer {user_token}"}
                
                response = self.session.get(f"{BACKEND_URL}/tasks", headers=headers)
                if response.status_code == 200:
                    user_tasks = response.json()
                    collaborative_tasks = [t for t in user_tasks if t['id'] == task['id']]
                    
                    if collaborative_tasks:
                        self.log_result(f"User {i+1} Task Visibility", True, f"User can see collaborative task")
                    else:
                        self.log_result(f"User {i+1} Task Visibility", False, "User cannot see collaborative task")
                else:
                    self.log_result(f"User {i+1} Task Visibility", False, f"HTTP {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log_result("Multi-user Collaboration", False, f"Error: {str(e)}")
            return False

    def test_data_isolation_and_security(self):
        """Test data isolation and security in collaborative environment"""
        print("\n=== Testing Data Isolation and Security ===")
        
        if len(self.test_data['users']) < 3:
            self.log_result("Data Security Setup", False, "Insufficient users")
            return False
        
        try:
            # Create a private task for user 1 (no collaborators)
            user1_token = self.test_data['tokens'][self.test_data['users'][0]['username']]
            headers = {"Authorization": f"Bearer {user1_token}"}
            
            private_task_data = {
                "title": f"Private Task {int(time.time())}",
                "description": "This task should only be visible to the owner",
                "priority": "medium",
                "estimated_duration": 120,
                "assigned_users": [],  # No assigned users
                "collaborators": [],   # No collaborators
                "tags": ["private"]
            }
            
            response = self.session.post(f"{BACKEND_URL}/tasks", json=private_task_data, headers=headers)
            if response.status_code == 200:
                private_task = response.json()
                self.log_result("Create Private Task", True, "Private task created")
                
                # Test that other users cannot access this private task
                for i, user in enumerate(self.test_data['users'][1:3]):
                    user_token = self.test_data['tokens'][user['username']]
                    user_headers = {"Authorization": f"Bearer {user_token}"}
                    
                    response = self.session.get(f"{BACKEND_URL}/tasks/{private_task['id']}", headers=user_headers)
                    if response.status_code == 404:
                        self.log_result(f"User {i+2} Private Task Isolation", True, "User cannot access private task")
                    else:
                        self.log_result(f"User {i+2} Private Task Isolation", False, f"User can access private task: HTTP {response.status_code}")
                
                # Clean up private task
                self.session.delete(f"{BACKEND_URL}/tasks/{private_task['id']}", headers=headers)
                
            else:
                self.log_result("Create Private Task", False, f"HTTP {response.status_code}")
            
            # Test project access control
            if self.test_data['projects']:
                project = self.test_data['projects'][0]
                
                # Test that non-collaborator cannot access project
                # Create a new user not in the project
                new_user_data = {
                    "email": f"outsider_{int(time.time())}@example.com",
                    "username": f"outsider_{int(time.time())}",
                    "full_name": "Outsider User",
                    "password": "OutsiderPass123"
                }
                
                response = self.session.post(f"{BACKEND_URL}/auth/register", json=new_user_data)
                if response.status_code == 200:
                    outsider_result = response.json()
                    outsider_token = outsider_result['access_token']
                    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}
                    
                    response = self.session.get(f"{BACKEND_URL}/projects/{project['id']}", headers=outsider_headers)
                    if response.status_code == 404:
                        self.log_result("Project Access Control", True, "Non-collaborator cannot access project")
                    else:
                        self.log_result("Project Access Control", False, f"Non-collaborator can access project: HTTP {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log_result("Data Isolation and Security", False, f"Error: {str(e)}")
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
        """Run all comprehensive collaborative features tests"""
        print("🚀 Starting Comprehensive Real-time Collaborative Features Testing")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"WebSocket URL: {WEBSOCKET_URL}")
        print("=" * 80)
        
        # Test sequence
        tests = [
            self.setup_test_users,
            self.test_team_management_comprehensive,
            self.test_project_team_integration,
            self.test_collaborative_task_creation,
            self.test_websocket_authentication,
            self.test_real_time_task_updates,
            self.test_multi_user_collaboration,
            self.test_data_isolation_and_security
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
        print("\n" + "=" * 80)
        print("🏁 COMPREHENSIVE COLLABORATIVE FEATURES TEST RESULTS")
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
    tester = ComprehensiveCollaborativeTest()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All comprehensive collaborative features tests passed!")
        exit(0)
    else:
        print(f"\n⚠️  {tester.results['failed']} tests failed.")
        exit(1)