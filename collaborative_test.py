#!/usr/bin/env python3
"""
Comprehensive Collaborative Real-time Features Testing Suite for TaskFlow Pro
Tests WebSocket connections, team-based task visibility, real-time updates, and multi-user collaboration
Focus: Testing all collaborative features as requested by the user
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
import jwt as jwt_lib

# Configuration
BACKEND_URL = "https://5f9f27c3-39df-42c0-9993-777740083949.preview.emergentagent.com/api"
WEBSOCKET_URL = "wss://5f9f27c3-39df-42c0-9993-777740083949.preview.emergentagent.com/ws"
TIMEOUT = 30

class CollaborativeFeaturesTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = TIMEOUT
        self.test_data = {
            'admin_user': None,
            'regular_users': [],
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
        self.websocket_messages = {}

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

    def test_user_authentication_setup(self):
        """Set up test users with authentication"""
        print("\n=== Setting Up Test Users with Authentication ===")
        
        try:
            # Create admin user
            admin_data = {
                "email": "admin@taskflow.com",
                "username": "admin",
                "full_name": "Admin User",
                "password": "AdminPassword123",
                "role": "admin"
            }
            
            response = self.session.post(f"{BACKEND_URL}/auth/register", json=admin_data)
            if response.status_code == 200:
                admin_result = response.json()
                self.test_data['admin_user'] = admin_result['user']
                self.test_data['tokens']['admin'] = admin_result['access_token']
                self.log_result("Admin User Registration", True, f"Admin user created: {admin_result['user']['email']}")
            else:
                # Try to login if user already exists
                login_data = {"email": admin_data["email"], "password": admin_data["password"]}
                response = self.session.post(f"{BACKEND_URL}/auth/login", json=login_data)
                if response.status_code == 200:
                    admin_result = response.json()
                    self.test_data['admin_user'] = admin_result['user']
                    self.test_data['tokens']['admin'] = admin_result['access_token']
                    self.log_result("Admin User Login", True, f"Admin user logged in: {admin_result['user']['email']}")
                else:
                    self.log_result("Admin User Setup", False, f"Failed to create/login admin: {response.text}")
                    return False

            # Create regular test users - use existing credentials or create new ones
            test_users = [
                {
                    "email": "newuser@example.com",
                    "username": "newuser",
                    "full_name": "New User",
                    "password": "SecurePassword123"  # Try existing password
                },
                {
                    "email": "test@example.com", 
                    "username": "testuser",
                    "full_name": "Test User",
                    "password": "SecurePassword123"  # Try existing password
                },
                {
                    "email": "collab2024@example.com",  # Use different email
                    "username": "collaborator2024",
                    "full_name": "Collaborator User", 
                    "password": "CollabPass123"
                }
            ]
            
            for user_data in test_users:
                response = self.session.post(f"{BACKEND_URL}/auth/register", json=user_data)
                if response.status_code == 200:
                    user_result = response.json()
                    self.test_data['regular_users'].append(user_result['user'])
                    self.test_data['tokens'][user_result['user']['username']] = user_result['access_token']
                    self.log_result(f"User Registration - {user_data['username']}", True, f"User created: {user_result['user']['email']}")
                else:
                    # Try to login if user already exists
                    login_data = {"email": user_data["email"], "password": user_data["password"]}
                    response = self.session.post(f"{BACKEND_URL}/auth/login", json=login_data)
                    if response.status_code == 200:
                        user_result = response.json()
                        self.test_data['regular_users'].append(user_result['user'])
                        self.test_data['tokens'][user_result['user']['username']] = user_result['access_token']
                        self.log_result(f"User Login - {user_data['username']}", True, f"User logged in: {user_result['user']['email']}")
                    else:
                        self.log_result(f"User Setup - {user_data['username']}", False, f"Failed to create/login: {response.text}")
            
            return len(self.test_data['regular_users']) >= 2
            
        except Exception as e:
            self.log_result("User Authentication Setup", False, f"Error: {str(e)}")
            return False

    def test_team_management_apis(self):
        """Test team creation and management APIs"""
        print("\n=== Testing Team Management APIs ===")
        
        if not self.test_data['admin_user'] or not self.test_data['regular_users']:
            self.log_result("Team Management Setup", False, "Admin user or regular users not available")
            return False
        
        try:
            # Set admin authorization header
            admin_token = self.test_data['tokens']['admin']
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Create a development team
            team_data = {
                "name": "Development Team",
                "description": "Main development team for TaskFlow Pro",
                "team_lead_id": self.test_data['regular_users'][0]['id'],
                "members": [user['id'] for user in self.test_data['regular_users'][:2]]
            }
            
            response = self.session.post(f"{BACKEND_URL}/admin/teams", json=team_data, headers=headers)
            if response.status_code == 200:
                team = response.json()
                self.test_data['teams'].append(team)
                self.log_result("Create Team", True, f"Team created: {team['name']} with {len(team['members'])} members")
                
                # Test get all teams
                response = self.session.get(f"{BACKEND_URL}/admin/teams", headers=headers)
                if response.status_code == 200:
                    teams = response.json()
                    if len(teams) > 0:
                        self.log_result("Get All Teams", True, f"Retrieved {len(teams)} teams")
                    else:
                        self.log_result("Get All Teams", False, "No teams returned")
                else:
                    self.log_result("Get All Teams", False, f"HTTP {response.status_code}")
                
                # Test get specific team
                response = self.session.get(f"{BACKEND_URL}/admin/teams/{team['id']}", headers=headers)
                if response.status_code == 200:
                    retrieved_team = response.json()
                    if retrieved_team['name'] == team['name']:
                        self.log_result("Get Team by ID", True, "Team retrieved successfully")
                    else:
                        self.log_result("Get Team by ID", False, "Team data mismatch")
                else:
                    self.log_result("Get Team by ID", False, f"HTTP {response.status_code}")
                
                return True
            else:
                self.log_result("Create Team", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Team Management APIs", False, f"Error: {str(e)}")
            return False

    def test_project_team_integration(self):
        """Test project creation with team integration"""
        print("\n=== Testing Project-Team Integration ===")
        
        if not self.test_data['teams'] or not self.test_data['regular_users']:
            self.log_result("Project-Team Integration Setup", False, "Teams or users not available")
            return False
        
        try:
            # Use first regular user's token
            user_token = self.test_data['tokens'][self.test_data['regular_users'][0]['username']]
            headers = {"Authorization": f"Bearer {user_token}"}
            
            # Create project with team collaboration
            project_data = {
                "name": "Collaborative Task Management System",
                "description": "Building a collaborative task management system with real-time features",
                "collaborators": [user['id'] for user in self.test_data['regular_users'][1:3]],
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
            }
            
            response = self.session.post(f"{BACKEND_URL}/projects", json=project_data, headers=headers)
            if response.status_code == 200:
                project = response.json()
                self.test_data['projects'].append(project)
                self.log_result("Create Collaborative Project", True, f"Project created: {project['name']} with {len(project['collaborators'])} collaborators")
                
                # Verify project access for collaborators
                for i, collaborator in enumerate(self.test_data['regular_users'][1:3]):
                    collab_token = self.test_data['tokens'][collaborator['username']]
                    collab_headers = {"Authorization": f"Bearer {collab_token}"}
                    
                    response = self.session.get(f"{BACKEND_URL}/projects/{project['id']}", headers=collab_headers)
                    if response.status_code == 200:
                        self.log_result(f"Collaborator {i+1} Project Access", True, f"Collaborator can access project")
                    else:
                        self.log_result(f"Collaborator {i+1} Project Access", False, f"HTTP {response.status_code}")
                
                return True
            else:
                self.log_result("Create Collaborative Project", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Project-Team Integration", False, f"Error: {str(e)}")
            return False

    def test_collaborative_task_creation(self):
        """Test task creation with collaborators and assigned users"""
        print("\n=== Testing Collaborative Task Creation ===")
        
        if not self.test_data['projects'] or not self.test_data['regular_users']:
            self.log_result("Collaborative Task Setup", False, "Projects or users not available")
            return False
        
        try:
            project = self.test_data['projects'][0]
            owner_token = self.test_data['tokens'][self.test_data['regular_users'][0]['username']]
            headers = {"Authorization": f"Bearer {owner_token}"}
            
            # Create task with collaborators and assigned users
            task_data = {
                "title": "Implement Real-time WebSocket Communication",
                "description": "Build WebSocket endpoints for real-time task updates and collaboration",
                "priority": "high",
                "project_id": project['id'],
                "estimated_duration": 480,  # 8 hours
                "due_date": (datetime.utcnow() + timedelta(days=5)).isoformat(),
                "assigned_users": [self.test_data['regular_users'][1]['id']],
                "collaborators": [self.test_data['regular_users'][2]['id']],
                "tags": ["websocket", "real-time", "collaboration"]
            }
            
            response = self.session.post(f"{BACKEND_URL}/tasks", json=task_data, headers=headers)
            if response.status_code == 200:
                task = response.json()
                self.test_data['tasks'].append(task)
                self.log_result("Create Collaborative Task", True, f"Task created with {len(task['assigned_users'])} assigned users and {len(task['collaborators'])} collaborators")
                
                # Test task visibility for assigned user
                assigned_user_token = self.test_data['tokens'][self.test_data['regular_users'][1]['username']]
                assigned_headers = {"Authorization": f"Bearer {assigned_user_token}"}
                
                response = self.session.get(f"{BACKEND_URL}/tasks/{task['id']}", headers=assigned_headers)
                if response.status_code == 200:
                    self.log_result("Assigned User Task Access", True, "Assigned user can access task")
                else:
                    self.log_result("Assigned User Task Access", False, f"HTTP {response.status_code}")
                
                # Test task visibility for collaborator
                collaborator_token = self.test_data['tokens'][self.test_data['regular_users'][2]['username']]
                collab_headers = {"Authorization": f"Bearer {collaborator_token}"}
                
                response = self.session.get(f"{BACKEND_URL}/tasks/{task['id']}", headers=collab_headers)
                if response.status_code == 200:
                    self.log_result("Collaborator Task Access", True, "Collaborator can access task")
                else:
                    self.log_result("Collaborator Task Access", False, f"HTTP {response.status_code}")
                
                return True
            else:
                self.log_result("Create Collaborative Task", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Collaborative Task Creation", False, f"Error: {str(e)}")
            return False

    def test_team_based_task_visibility(self):
        """Test that team members can see tasks from team projects"""
        print("\n=== Testing Team-based Task Visibility ===")
        
        if not self.test_data['tasks'] or not self.test_data['regular_users']:
            self.log_result("Team Task Visibility Setup", False, "Tasks or users not available")
            return False
        
        try:
            # Test task visibility for different users
            for i, user in enumerate(self.test_data['regular_users'][:3]):
                user_token = self.test_data['tokens'][user['username']]
                headers = {"Authorization": f"Bearer {user_token}"}
                
                response = self.session.get(f"{BACKEND_URL}/tasks", headers=headers)
                if response.status_code == 200:
                    tasks = response.json()
                    self.log_result(f"User {i+1} Task Visibility", True, f"User {user['username']} can see {len(tasks)} tasks")
                    
                    # Check if user can see collaborative tasks
                    collaborative_tasks = [t for t in tasks if user['id'] in t.get('assigned_users', []) + t.get('collaborators', []) or t.get('owner_id') == user['id']]
                    if len(collaborative_tasks) > 0:
                        self.log_result(f"User {i+1} Collaborative Access", True, f"User has access to {len(collaborative_tasks)} collaborative tasks")
                    else:
                        self.log_result(f"User {i+1} Collaborative Access", False, "User has no collaborative task access")
                else:
                    self.log_result(f"User {i+1} Task Visibility", False, f"HTTP {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log_result("Team-based Task Visibility", False, f"Error: {str(e)}")
            return False

    def test_websocket_authentication(self):
        """Test WebSocket connection with JWT authentication"""
        print("\n=== Testing WebSocket Authentication ===")
        
        if not self.test_data['regular_users']:
            self.log_result("WebSocket Auth Setup", False, "Regular users not available")
            return False
        
        try:
            user = self.test_data['regular_users'][0]
            token = self.test_data['tokens'][user['username']]
            
            # Test WebSocket connection with valid token
            async def test_websocket_connection():
                try:
                    uri = f"{WEBSOCKET_URL}/{user['id']}?token={token}"
                    async with websockets.connect(uri) as websocket:
                        # Wait for welcome message
                        message = await asyncio.wait_for(websocket.recv(), timeout=5)
                        data = json.loads(message)
                        
                        if data.get('type') == 'connection_established':
                            return True, "WebSocket connection established successfully"
                        else:
                            return False, f"Unexpected welcome message: {data}"
                            
                except asyncio.TimeoutError:
                    return False, "WebSocket connection timeout"
                except Exception as e:
                    return False, f"WebSocket connection error: {str(e)}"
            
            # Run async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, message = loop.run_until_complete(test_websocket_connection())
            loop.close()
            
            self.log_result("WebSocket JWT Authentication", success, message)
            
            # Test WebSocket connection with invalid token
            async def test_invalid_token():
                try:
                    invalid_token = "invalid.jwt.token"
                    uri = f"{WEBSOCKET_URL}/{user['id']}?token={invalid_token}"
                    async with websockets.connect(uri) as websocket:
                        await asyncio.wait_for(websocket.recv(), timeout=3)
                        return False, "Connection should have been rejected"
                except websockets.exceptions.ConnectionClosedError as e:
                    if e.code == 1008:  # Policy violation (invalid token)
                        return True, "Invalid token properly rejected"
                    else:
                        return False, f"Unexpected close code: {e.code}"
                except Exception as e:
                    return True, f"Connection properly rejected: {str(e)}"
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, message = loop.run_until_complete(test_invalid_token())
            loop.close()
            
            self.log_result("WebSocket Invalid Token Rejection", success, message)
            
            return True
            
        except Exception as e:
            self.log_result("WebSocket Authentication", False, f"Error: {str(e)}")
            return False

    def test_real_time_task_updates(self):
        """Test real-time task updates via WebSocket"""
        print("\n=== Testing Real-time Task Updates ===")
        
        if not self.test_data['tasks'] or len(self.test_data['regular_users']) < 2:
            self.log_result("Real-time Updates Setup", False, "Tasks or users not available")
            return False
        
        try:
            task = self.test_data['tasks'][0]
            owner = self.test_data['regular_users'][0]
            collaborator = self.test_data['regular_users'][1]
            
            owner_token = self.test_data['tokens'][owner['username']]
            collab_token = self.test_data['tokens'][collaborator['username']]
            
            received_updates = []
            
            async def websocket_listener(user_id, token, updates_list):
                """Listen for WebSocket updates"""
                try:
                    uri = f"{WEBSOCKET_URL}/{user_id}?token={token}"
                    async with websockets.connect(uri) as websocket:
                        # Skip welcome message
                        await websocket.recv()
                        
                        # Listen for updates for 10 seconds
                        try:
                            while True:
                                message = await asyncio.wait_for(websocket.recv(), timeout=10)
                                data = json.loads(message)
                                if data.get('type') == 'task_update':
                                    updates_list.append(data)
                        except asyncio.TimeoutError:
                            pass  # Expected timeout
                            
                except Exception as e:
                    print(f"WebSocket listener error: {str(e)}")
            
            async def test_real_time_updates():
                # Start WebSocket listener for collaborator
                listener_task = asyncio.create_task(
                    websocket_listener(collaborator['id'], collab_token, received_updates)
                )
                
                # Wait a moment for connection
                await asyncio.sleep(2)
                
                # Update task via REST API
                update_data = {
                    "status": "in_progress",
                    "description": "Updated description for real-time testing"
                }
                
                headers = {"Authorization": f"Bearer {owner_token}"}
                response = requests.put(f"{BACKEND_URL}/tasks/{task['id']}", json=update_data, headers=headers)
                
                if response.status_code == 200:
                    # Wait for WebSocket update
                    await asyncio.sleep(3)
                    
                    # Cancel listener
                    listener_task.cancel()
                    
                    return len(received_updates) > 0, f"Received {len(received_updates)} real-time updates"
                else:
                    listener_task.cancel()
                    return False, f"Task update failed: HTTP {response.status_code}"
            
            # Run async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, message = loop.run_until_complete(test_real_time_updates())
            loop.close()
            
            self.log_result("Real-time Task Updates", success, message)
            
            if received_updates:
                update = received_updates[0]
                if update.get('action') == 'updated' and update.get('task', {}).get('id') == task['id']:
                    self.log_result("Real-time Update Content", True, "Update contains correct task data")
                else:
                    self.log_result("Real-time Update Content", False, "Update content incorrect")
            
            return success
            
        except Exception as e:
            self.log_result("Real-time Task Updates", False, f"Error: {str(e)}")
            return False

    def test_multi_user_data_access(self):
        """Test multi-user data access patterns"""
        print("\n=== Testing Multi-user Data Access ===")
        
        if not self.test_data['regular_users'] or not self.test_data['tasks']:
            self.log_result("Multi-user Access Setup", False, "Users or tasks not available")
            return False
        
        try:
            # Test data isolation - users should only see their own data plus collaborative data
            for i, user in enumerate(self.test_data['regular_users'][:3]):
                user_token = self.test_data['tokens'][user['username']]
                headers = {"Authorization": f"Bearer {user_token}"}
                
                # Get user's tasks
                response = self.session.get(f"{BACKEND_URL}/tasks", headers=headers)
                if response.status_code == 200:
                    user_tasks = response.json()
                    
                    # Verify user can only see appropriate tasks
                    accessible_tasks = []
                    for task in user_tasks:
                        if (task.get('owner_id') == user['id'] or 
                            user['id'] in task.get('assigned_users', []) or 
                            user['id'] in task.get('collaborators', [])):
                            accessible_tasks.append(task)
                    
                    if len(accessible_tasks) == len(user_tasks):
                        self.log_result(f"User {i+1} Data Access Control", True, f"User sees {len(user_tasks)} appropriate tasks")
                    else:
                        self.log_result(f"User {i+1} Data Access Control", False, f"User sees unauthorized tasks")
                    
                    # Get user's projects
                    response = self.session.get(f"{BACKEND_URL}/projects", headers=headers)
                    if response.status_code == 200:
                        user_projects = response.json()
                        self.log_result(f"User {i+1} Project Access", True, f"User sees {len(user_projects)} projects")
                    else:
                        self.log_result(f"User {i+1} Project Access", False, f"HTTP {response.status_code}")
                        
                else:
                    self.log_result(f"User {i+1} Task Access", False, f"HTTP {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log_result("Multi-user Data Access", False, f"Error: {str(e)}")
            return False

    def test_task_assignment_collaboration(self):
        """Test task assignment and collaboration workflows"""
        print("\n=== Testing Task Assignment & Collaboration ===")
        
        if not self.test_data['tasks'] or len(self.test_data['regular_users']) < 3:
            self.log_result("Task Assignment Setup", False, "Tasks or users not available")
            return False
        
        try:
            task = self.test_data['tasks'][0]
            owner_token = self.test_data['tokens'][self.test_data['regular_users'][0]['username']]
            headers = {"Authorization": f"Bearer {owner_token}"}
            
            # Update task to add more collaborators
            update_data = {
                "assigned_users": [user['id'] for user in self.test_data['regular_users'][1:3]],
                "collaborators": [self.test_data['regular_users'][2]['id']],
                "description": "Updated task with multiple assigned users and collaborators"
            }
            
            response = self.session.put(f"{BACKEND_URL}/tasks/{task['id']}", json=update_data, headers=headers)
            if response.status_code == 200:
                updated_task = response.json()
                
                if len(updated_task['assigned_users']) == 2:
                    self.log_result("Task Assignment Update", True, f"Task now has {len(updated_task['assigned_users'])} assigned users")
                else:
                    self.log_result("Task Assignment Update", False, "Assigned users not updated correctly")
                
                # Test that all assigned users can access the task
                for i, user in enumerate(self.test_data['regular_users'][1:3]):
                    user_token = self.test_data['tokens'][user['username']]
                    user_headers = {"Authorization": f"Bearer {user_token}"}
                    
                    response = self.session.get(f"{BACKEND_URL}/tasks/{task['id']}", headers=user_headers)
                    if response.status_code == 200:
                        self.log_result(f"Assigned User {i+1} Access", True, "Assigned user can access task")
                    else:
                        self.log_result(f"Assigned User {i+1} Access", False, f"HTTP {response.status_code}")
                
                # Test that assigned users can update the task
                assigned_user_token = self.test_data['tokens'][self.test_data['regular_users'][1]['username']]
                assigned_headers = {"Authorization": f"Bearer {assigned_user_token}"}
                
                update_by_assigned = {"status": "in_progress"}
                response = self.session.put(f"{BACKEND_URL}/tasks/{task['id']}", json=update_by_assigned, headers=assigned_headers)
                if response.status_code == 200:
                    self.log_result("Assigned User Can Update", True, "Assigned user can update task")
                else:
                    self.log_result("Assigned User Can Update", False, f"HTTP {response.status_code}")
                
                return True
            else:
                self.log_result("Task Assignment Update", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Task Assignment & Collaboration", False, f"Error: {str(e)}")
            return False

    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n=== Cleaning Up Test Data ===")
        
        try:
            # Delete test tasks
            if self.test_data['tasks']:
                owner_token = self.test_data['tokens'][self.test_data['regular_users'][0]['username']]
                headers = {"Authorization": f"Bearer {owner_token}"}
                
                for task in self.test_data['tasks']:
                    try:
                        response = self.session.delete(f"{BACKEND_URL}/tasks/{task['id']}", headers=headers)
                        if response.status_code == 200:
                            print(f"✅ Deleted task: {task['title']}")
                        else:
                            print(f"❌ Failed to delete task: {task['title']}")
                    except Exception as e:
                        print(f"❌ Error deleting task {task['title']}: {str(e)}")
            
            # Delete test teams (admin only)
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
        print("🚀 Starting Comprehensive Collaborative Real-time Features Testing Suite")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"WebSocket URL: {WEBSOCKET_URL}")
        print("=" * 80)
        
        # Test sequence
        tests = [
            self.test_user_authentication_setup,
            self.test_team_management_apis,
            self.test_project_team_integration,
            self.test_collaborative_task_creation,
            self.test_team_based_task_visibility,
            self.test_websocket_authentication,
            self.test_real_time_task_updates,
            self.test_multi_user_data_access,
            self.test_task_assignment_collaboration
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
        print("🏁 COLLABORATIVE FEATURES TEST RESULTS")
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
    tester = CollaborativeFeaturesTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All collaborative features tests passed! Real-time collaboration is working correctly.")
        exit(0)
    else:
        print(f"\n⚠️  {tester.results['failed']} tests failed. Check the issues above.")
        exit(1)