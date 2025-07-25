#!/usr/bin/env python3
"""
Comprehensive Backend Testing Suite for Task Management System with Authentication
Tests all backend APIs including authentication, CRUD operations, analytics, and performance metrics
Focus: User authentication system with JWT tokens, password validation, and data isolation
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
BACKEND_URL = "https://5dc9bda8-f77f-4ebb-a8cf-c1393001bfb1.preview.emergentagent.com/api"
TIMEOUT = 30

class TaskManagementTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = TIMEOUT
        self.test_data = {
            'users': [],
            'projects': [],
            'tasks': [],
            'subtasks': []
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

    def test_api_connectivity(self):
        """Test basic API connectivity"""
        print("\n=== Testing API Connectivity ===")
        try:
            response = self.session.get(f"{BACKEND_URL}/")
            if response.status_code == 200:
                data = response.json()
                if "Task Management API" in data.get("message", ""):
                    self.log_result("API Connectivity", True, f"API responding: {data['message']}")
                    return True
                else:
                    self.log_result("API Connectivity", False, f"Unexpected response: {data}")
                    return False
            else:
                self.log_result("API Connectivity", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("API Connectivity", False, f"Connection error: {str(e)}")
            return False

    def test_project_crud(self):
        """Test Project CRUD operations with authentication"""
        print("\n=== Testing Project CRUD Operations ===")
        
        if not self.test_data['users']:
            self.log_result("Project CRUD Setup", False, "No authenticated users available")
            return False
        
        user1 = self.test_data['users'][0]
        user2 = self.test_data['users'][1] if len(self.test_data['users']) > 1 else user1
        
        # Test Create Project
        project_data = {
            "name": "Subtask Management System",
            "description": "Building comprehensive subtask management with comments and collaboration",
            "collaborators": [user2['token_data']['user']['id']] if user2 != user1 else [],
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        
        try:
            response = self.session.post(f"{BACKEND_URL}/projects", json=project_data, headers=user1['headers'])
            if response.status_code == 200:
                project = response.json()
                self.test_data['projects'].append(project)
                self.log_result("Create Project", True, f"Created project: {project['name']}")
                
                # Test Get Project
                response = self.session.get(f"{BACKEND_URL}/projects/{project['id']}", headers=user1['headers'])
                if response.status_code == 200:
                    retrieved_project = response.json()
                    if retrieved_project['name'] == project_data['name']:
                        self.log_result("Get Project by ID", True, "Project retrieved successfully")
                    else:
                        self.log_result("Get Project by ID", False, "Retrieved project data mismatch")
                else:
                    self.log_result("Get Project by ID", False, f"HTTP {response.status_code}")
                
                # Test Get All Projects
                response = self.session.get(f"{BACKEND_URL}/projects", headers=user1['headers'])
                if response.status_code == 200:
                    projects = response.json()
                    if isinstance(projects, list) and len(projects) > 0:
                        self.log_result("Get All Projects", True, f"Retrieved {len(projects)} projects")
                    else:
                        self.log_result("Get All Projects", False, "No projects returned")
                else:
                    self.log_result("Get All Projects", False, f"HTTP {response.status_code}")
                
                return True
            else:
                self.log_result("Create Project", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Project CRUD", False, f"Error: {str(e)}")
            return False

    def test_task_crud_with_analytics(self):
        """Test Task CRUD operations with analytics tracking"""
        print("\n=== Testing Task CRUD with Analytics Tracking ===")
        
        if not self.test_data['projects'] or not self.test_data['users']:
            self.log_result("Task CRUD Setup", False, "No projects or authenticated users available")
            return False
        
        project = self.test_data['projects'][0]
        user1 = self.test_data['users'][0]
        user2 = self.test_data['users'][1] if len(self.test_data['users']) > 1 else user1
        
        # Test Create Task
        task_data = {
            "title": "Implement Subtask Management System",
            "description": "Build comprehensive subtask management with CRUD operations, comments, and user assignments",
            "priority": "high",
            "project_id": project['id'],
            "estimated_duration": 480,  # 8 hours in minutes
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "assigned_users": [user1['token_data']['user']['id'], user2['token_data']['user']['id']] if user2 != user1 else [user1['token_data']['user']['id']],
            "collaborators": [user2['token_data']['user']['id']] if user2 != user1 else [],
            "tags": ["subtasks", "backend", "high-priority"]
        }
        
        try:
            response = self.session.post(f"{BACKEND_URL}/tasks", json=task_data, headers=user1['headers'])
            if response.status_code == 200:
                task = response.json()
                self.test_data['tasks'].append(task)
                
                # Verify project name was set
                if task.get('project_name') == project['name']:
                    self.log_result("Create Task with Project Link", True, f"Task created with project: {task['project_name']}")
                else:
                    self.log_result("Create Task with Project Link", False, "Project name not set correctly")
                
                # Test Get Task
                response = self.session.get(f"{BACKEND_URL}/tasks/{task['id']}", headers=user1['headers'])
                if response.status_code == 200:
                    retrieved_task = response.json()
                    self.log_result("Get Task by ID", True, "Task retrieved successfully")
                else:
                    self.log_result("Get Task by ID", False, f"HTTP {response.status_code}")
                
                # Test Update Task Status (Analytics Tracking)
                update_data = {
                    "status": "in_progress",
                    "actual_duration": 120  # 2 hours
                }
                response = self.session.put(f"{BACKEND_URL}/tasks/{task['id']}", json=update_data, headers=user1['headers'])
                if response.status_code == 200:
                    updated_task = response.json()
                    if updated_task['status'] == 'in_progress':
                        self.log_result("Update Task Status", True, "Task status updated to in_progress")
                    else:
                        self.log_result("Update Task Status", False, "Status not updated correctly")
                else:
                    self.log_result("Update Task Status", False, f"HTTP {response.status_code}")
                
                # Test Complete Task (Analytics Tracking)
                complete_data = {
                    "status": "completed",
                    "actual_duration": 450  # 7.5 hours
                }
                response = self.session.put(f"{BACKEND_URL}/tasks/{task['id']}", json=complete_data, headers=user1['headers'])
                if response.status_code == 200:
                    completed_task = response.json()
                    if completed_task['status'] == 'completed' and completed_task.get('completed_at'):
                        self.log_result("Complete Task with Analytics", True, "Task completed with timestamp")
                    else:
                        self.log_result("Complete Task with Analytics", False, "Completion not tracked properly")
                else:
                    self.log_result("Complete Task with Analytics", False, f"HTTP {response.status_code}")
                
                # Test Get Tasks with Filters
                response = self.session.get(f"{BACKEND_URL}/tasks?project_id={project['id']}", headers=user1['headers'])
                if response.status_code == 200:
                    project_tasks = response.json()
                    if len(project_tasks) > 0:
                        self.log_result("Get Tasks by Project", True, f"Found {len(project_tasks)} tasks for project")
                    else:
                        self.log_result("Get Tasks by Project", False, "No tasks found for project")
                else:
                    self.log_result("Get Tasks by Project", False, f"HTTP {response.status_code}")
                
                return True
            else:
                self.log_result("Create Task", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Task CRUD", False, f"Error: {str(e)}")
            return False

    def test_analytics_dashboard(self):
        """Test Analytics Dashboard endpoint"""
        print("\n=== Testing Analytics Dashboard ===")
        
        if not self.test_data['users']:
            self.log_result("Analytics Dashboard Setup", False, "No authenticated users available")
            return False
        
        user1 = self.test_data['users'][0]
        
        try:
            response = self.session.get(f"{BACKEND_URL}/analytics/dashboard", headers=user1['headers'])
            if response.status_code == 200:
                analytics = response.json()
                
                # Check overview data
                if 'overview' in analytics:
                    overview = analytics['overview']
                    required_fields = ['total_tasks', 'completed_tasks', 'in_progress_tasks', 'completion_rate', 'total_projects']
                    
                    if all(field in overview for field in required_fields):
                        self.log_result("Dashboard Overview Data", True, f"All required fields present. Completion rate: {overview['completion_rate']}%")
                    else:
                        missing = [f for f in required_fields if f not in overview]
                        self.log_result("Dashboard Overview Data", False, f"Missing fields: {missing}")
                else:
                    self.log_result("Dashboard Overview Data", False, "No overview section in response")
                
                # Check productivity trends
                if 'productivity_trends' in analytics:
                    trends = analytics['productivity_trends']
                    if isinstance(trends, list) and len(trends) == 7:
                        self.log_result("7-Day Productivity Trends", True, f"Retrieved {len(trends)} days of trend data")
                        
                        # Verify trend data structure
                        if trends and all('date' in trend and 'tasks_completed' in trend for trend in trends):
                            self.log_result("Productivity Trends Structure", True, "Trend data properly structured")
                        else:
                            self.log_result("Productivity Trends Structure", False, "Trend data missing required fields")
                    else:
                        self.log_result("7-Day Productivity Trends", False, f"Expected 7 days, got {len(trends) if isinstance(trends, list) else 'invalid'}")
                else:
                    self.log_result("7-Day Productivity Trends", False, "No productivity_trends in response")
                
                return True
            else:
                self.log_result("Analytics Dashboard", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Analytics Dashboard", False, f"Error: {str(e)}")
            return False

    def test_project_analytics(self):
        """Test Project Analytics endpoint"""
        print("\n=== Testing Project Analytics ===")
        
        if not self.test_data['projects'] or not self.test_data['users']:
            self.log_result("Project Analytics", False, "No projects or authenticated users available")
            return False
        
        project = self.test_data['projects'][0]
        user1 = self.test_data['users'][0]
        
        try:
            response = self.session.get(f"{BACKEND_URL}/projects/{project['id']}/analytics", headers=user1['headers'])
            if response.status_code == 200:
                analytics = response.json()
                
                required_fields = ['total_tasks', 'completed_tasks', 'progress_percentage', 'total_estimated_time', 'total_actual_time']
                
                if all(field in analytics for field in required_fields):
                    self.log_result("Project Analytics Data", True, f"Progress: {analytics['progress_percentage']}%, Tasks: {analytics['total_tasks']}")
                    
                    # Verify calculations make sense
                    if analytics['total_tasks'] >= analytics['completed_tasks']:
                        self.log_result("Project Analytics Logic", True, "Task counts are logical")
                    else:
                        self.log_result("Project Analytics Logic", False, "Completed tasks exceed total tasks")
                else:
                    missing = [f for f in required_fields if f not in analytics]
                    self.log_result("Project Analytics Data", False, f"Missing fields: {missing}")
                
                return True
            else:
                self.log_result("Project Analytics", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Project Analytics", False, f"Error: {str(e)}")
            return False

    def test_performance_metrics(self):
        """Test Performance Metrics APIs"""
        print("\n=== Testing Performance Metrics ===")
        
        if not self.test_data['users']:
            self.log_result("Performance Metrics Setup", False, "No authenticated users available")
            return False
        
        user1 = self.test_data['users'][0]
        
        try:
            # Test User Performance Analytics
            response = self.session.get(f"{BACKEND_URL}/analytics/performance?days=7", headers=user1['headers'])
            if response.status_code == 200:
                performance = response.json()
                
                if 'performance_data' in performance and isinstance(performance['performance_data'], list):
                    perf_data = performance['performance_data']
                    if len(perf_data) == 7:
                        self.log_result("User Performance Analytics", True, f"Retrieved 7 days of performance data")
                        
                        # Check data structure
                        if perf_data and all('date' in day and 'productivity_score' in day for day in perf_data):
                            self.log_result("Performance Data Structure", True, "Performance data properly structured")
                        else:
                            self.log_result("Performance Data Structure", False, "Performance data missing required fields")
                    else:
                        self.log_result("User Performance Analytics", False, f"Expected 7 days, got {len(perf_data)}")
                else:
                    self.log_result("User Performance Analytics", False, "No performance_data in response")
            else:
                self.log_result("User Performance Analytics", False, f"HTTP {response.status_code}")
            
            # Test Time Tracking Analytics
            response = self.session.get(f"{BACKEND_URL}/analytics/time-tracking", headers=user1['headers'])
            if response.status_code == 200:
                time_analytics = response.json()
                
                required_fields = ['time_by_project', 'time_by_priority', 'total_estimated_hours', 'total_actual_hours', 'accuracy_percentage']
                
                if all(field in time_analytics for field in required_fields):
                    self.log_result("Time Tracking Analytics", True, f"Accuracy: {time_analytics['accuracy_percentage']}%")
                else:
                    missing = [f for f in required_fields if f not in time_analytics]
                    self.log_result("Time Tracking Analytics", False, f"Missing fields: {missing}")
            else:
                self.log_result("Time Tracking Analytics", False, f"HTTP {response.status_code}")
            
            return True
        except Exception as e:
            self.log_result("Performance Metrics", False, f"Error: {str(e)}")
            return False

    def test_data_relationships(self):
        """Test data relationships and consistency"""
        print("\n=== Testing Data Relationships ===")
        
        if not self.test_data['projects'] or not self.test_data['tasks'] or not self.test_data['users']:
            self.log_result("Data Relationships", False, "Insufficient test data")
            return False
        
        project = self.test_data['projects'][0]
        user1 = self.test_data['users'][0]
        
        try:
            # Get updated project to check task counts
            response = self.session.get(f"{BACKEND_URL}/projects/{project['id']}", headers=user1['headers'])
            if response.status_code == 200:
                updated_project = response.json()
                
                # Check if task count was updated
                if updated_project.get('task_count', 0) > 0:
                    self.log_result("Project Task Count Update", True, f"Project has {updated_project['task_count']} tasks")
                else:
                    self.log_result("Project Task Count Update", False, "Task count not updated")
                
                # Check completed task count
                if updated_project.get('completed_task_count', 0) > 0:
                    self.log_result("Project Completion Tracking", True, f"Project has {updated_project['completed_task_count']} completed tasks")
                else:
                    self.log_result("Project Completion Tracking", False, "Completed task count not tracked")
            else:
                self.log_result("Data Relationships", False, f"Could not retrieve updated project: HTTP {response.status_code}")
            
            return True
        except Exception as e:
            self.log_result("Data Relationships", False, f"Error: {str(e)}")
            return False

    def test_user_authentication(self):
        """Test user authentication system"""
        print("\n=== Testing User Authentication System ===")
        
        # Generate unique test users
        user1_email = f"testuser1_{uuid.uuid4().hex[:8]}@example.com"
        user2_email = f"testuser2_{uuid.uuid4().hex[:8]}@example.com"
        
        # Test User Registration
        user1_data = {
            "email": user1_email,
            "username": f"testuser1_{uuid.uuid4().hex[:6]}",
            "full_name": "Test User One",
            "password": "SecurePass123!"
        }
        
        user2_data = {
            "email": user2_email,
            "username": f"testuser2_{uuid.uuid4().hex[:6]}",
            "full_name": "Test User Two", 
            "password": "SecurePass456!"
        }
        
        try:
            # Register User 1
            response = self.session.post(f"{BACKEND_URL}/auth/register", json=user1_data)
            if response.status_code == 200:
                user1_token_data = response.json()
                self.test_data['users'].append({
                    'user_data': user1_data,
                    'token_data': user1_token_data,
                    'headers': {'Authorization': f"Bearer {user1_token_data['access_token']}"}
                })
                self.log_result("User 1 Registration", True, f"User registered: {user1_data['username']}")
            else:
                self.log_result("User 1 Registration", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            # Register User 2
            response = self.session.post(f"{BACKEND_URL}/auth/register", json=user2_data)
            if response.status_code == 200:
                user2_token_data = response.json()
                self.test_data['users'].append({
                    'user_data': user2_data,
                    'token_data': user2_token_data,
                    'headers': {'Authorization': f"Bearer {user2_token_data['access_token']}"}
                })
                self.log_result("User 2 Registration", True, f"User registered: {user2_data['username']}")
            else:
                self.log_result("User 2 Registration", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            # Test Login
            login_data = {"email": user1_email, "password": user1_data['password']}
            response = self.session.post(f"{BACKEND_URL}/auth/login", json=login_data)
            if response.status_code == 200:
                login_token_data = response.json()
                self.log_result("User Login", True, "Login successful with JWT token")
            else:
                self.log_result("User Login", False, f"HTTP {response.status_code}: {response.text}")
            
            return True
        except Exception as e:
            self.log_result("User Authentication", False, f"Error: {str(e)}")
            return False

    def test_subtask_crud_operations(self):
        """Test Subtask CRUD Operations"""
        print("\n=== Testing Subtask CRUD Operations ===")
        
        if not self.test_data['users'] or not self.test_data['tasks']:
            self.log_result("Subtask CRUD Setup", False, "No authenticated users or tasks available")
            return False
        
        user1 = self.test_data['users'][0]
        user2 = self.test_data['users'][1] if len(self.test_data['users']) > 1 else user1
        task = self.test_data['tasks'][0]
        
        try:
            # Test Create Subtask
            subtask_data = {
                "text": "Implement user authentication middleware",
                "description": "Add JWT token validation and user context extraction",
                "assigned_users": [user1['token_data']['user']['id'], user2['token_data']['user']['id']],
                "priority": "high",
                "due_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
                "estimated_duration": 120  # 2 hours
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/tasks/{task['id']}/subtasks",
                json=subtask_data,
                headers=user1['headers']
            )
            
            if response.status_code == 200:
                subtask = response.json()
                self.test_data['subtasks'] = [subtask]
                self.log_result("Create Subtask", True, f"Subtask created: {subtask['text']}")
                
                # Verify assigned usernames were populated
                if len(subtask.get('assigned_usernames', [])) == 2:
                    self.log_result("Subtask User Assignment", True, "Assigned usernames populated correctly")
                else:
                    self.log_result("Subtask User Assignment", False, "Assigned usernames not populated")
            else:
                self.log_result("Create Subtask", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            # Test Update Subtask
            subtask_id = subtask['id']
            update_data = {
                "text": "Implement enhanced JWT authentication middleware",
                "completed": True,
                "actual_duration": 90,  # 1.5 hours
                "priority": "urgent"
            }
            
            response = self.session.put(
                f"{BACKEND_URL}/tasks/{task['id']}/subtasks/{subtask_id}",
                json=update_data,
                headers=user1['headers']
            )
            
            if response.status_code == 200:
                updated_subtask = response.json()
                if updated_subtask['completed'] and updated_subtask['completed_at']:
                    self.log_result("Update Subtask", True, "Subtask updated and marked completed")
                else:
                    self.log_result("Update Subtask", False, "Subtask completion not tracked properly")
            else:
                self.log_result("Update Subtask", False, f"HTTP {response.status_code}: {response.text}")
            
            # Test Permission-based Access (User 2 should be able to access as assigned user)
            response = self.session.put(
                f"{BACKEND_URL}/tasks/{task['id']}/subtasks/{subtask_id}",
                json={"text": "Updated by assigned user"},
                headers=user2['headers']
            )
            
            if response.status_code == 200:
                self.log_result("Subtask Access by Assigned User", True, "Assigned user can update subtask")
            else:
                self.log_result("Subtask Access by Assigned User", False, f"HTTP {response.status_code}")
            
            # Test Delete Subtask
            response = self.session.delete(
                f"{BACKEND_URL}/tasks/{task['id']}/subtasks/{subtask_id}",
                headers=user1['headers']
            )
            
            if response.status_code == 200:
                self.log_result("Delete Subtask", True, "Subtask deleted successfully")
            else:
                self.log_result("Delete Subtask", False, f"HTTP {response.status_code}: {response.text}")
            
            return True
        except Exception as e:
            self.log_result("Subtask CRUD Operations", False, f"Error: {str(e)}")
            return False

    def test_subtask_comments_system(self):
        """Test Subtask Comments System"""
        print("\n=== Testing Subtask Comments System ===")
        
        if not self.test_data['users'] or not self.test_data['tasks']:
            self.log_result("Subtask Comments Setup", False, "No authenticated users or tasks available")
            return False
        
        user1 = self.test_data['users'][0]
        user2 = self.test_data['users'][1] if len(self.test_data['users']) > 1 else user1
        task = self.test_data['tasks'][0]
        
        try:
            # First create a subtask for comments testing
            subtask_data = {
                "text": "Design database schema for comments",
                "description": "Create MongoDB schema for subtask comments with threading support",
                "assigned_users": [user1['token_data']['user']['id']],
                "priority": "medium"
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/tasks/{task['id']}/subtasks",
                json=subtask_data,
                headers=user1['headers']
            )
            
            if response.status_code != 200:
                self.log_result("Subtask Comments Setup", False, "Could not create subtask for comments testing")
                return False
            
            subtask = response.json()
            subtask_id = subtask['id']
            
            # Test Add Comment
            comment_data = {"comment": "I think we should use a nested document structure for better performance"}
            
            response = self.session.post(
                f"{BACKEND_URL}/tasks/{task['id']}/subtasks/{subtask_id}/comments",
                json=comment_data,
                headers=user1['headers']
            )
            
            if response.status_code == 200:
                comment = response.json()
                comment_id = comment['id']
                self.log_result("Add Subtask Comment", True, f"Comment added by {comment['username']}")
                
                # Verify comment structure
                if comment['user_id'] == user1['token_data']['user']['id'] and comment['username']:
                    self.log_result("Comment User Attribution", True, "Comment properly attributed to user")
                else:
                    self.log_result("Comment User Attribution", False, "Comment attribution incorrect")
            else:
                self.log_result("Add Subtask Comment", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            # Test Add Second Comment (from different user)
            if user2 != user1:
                comment2_data = {"comment": "Good point! Let's also consider indexing strategies for better query performance"}
                
                response = self.session.post(
                    f"{BACKEND_URL}/tasks/{task['id']}/subtasks/{subtask_id}/comments",
                    json=comment2_data,
                    headers=user2['headers']
                )
                
                if response.status_code == 200:
                    comment2 = response.json()
                    self.log_result("Multi-user Comments", True, "Multiple users can add comments")
                else:
                    self.log_result("Multi-user Comments", False, f"HTTP {response.status_code}")
            
            # Test Update Comment (only by comment author)
            update_comment_data = {"comment": "Updated: I think we should use a nested document structure with proper indexing for optimal performance"}
            
            response = self.session.put(
                f"{BACKEND_URL}/tasks/{task['id']}/subtasks/{subtask_id}/comments/{comment_id}",
                json=update_comment_data,
                headers=user1['headers']
            )
            
            if response.status_code == 200:
                updated_comment = response.json()
                if updated_comment['comment'] == update_comment_data['comment']:
                    self.log_result("Update Comment by Author", True, "Comment author can update their comment")
                else:
                    self.log_result("Update Comment by Author", False, "Comment not updated properly")
            else:
                self.log_result("Update Comment by Author", False, f"HTTP {response.status_code}")
            
            # Test Update Comment Permission (different user should be denied)
            if user2 != user1:
                response = self.session.put(
                    f"{BACKEND_URL}/tasks/{task['id']}/subtasks/{subtask_id}/comments/{comment_id}",
                    json={"comment": "Trying to update someone else's comment"},
                    headers=user2['headers']
                )
                
                if response.status_code == 403:
                    self.log_result("Comment Update Permission", True, "Non-author cannot update comment (403 Forbidden)")
                else:
                    self.log_result("Comment Update Permission", False, f"Expected 403, got {response.status_code}")
            
            # Test Delete Comment (only by comment author)
            response = self.session.delete(
                f"{BACKEND_URL}/tasks/{task['id']}/subtasks/{subtask_id}/comments/{comment_id}",
                headers=user1['headers']
            )
            
            if response.status_code == 200:
                self.log_result("Delete Comment by Author", True, "Comment author can delete their comment")
            else:
                self.log_result("Delete Comment by Author", False, f"HTTP {response.status_code}")
            
            return True
        except Exception as e:
            self.log_result("Subtask Comments System", False, f"Error: {str(e)}")
            return False

    def test_subtask_integration_with_tasks(self):
        """Test Subtask Integration with Task System"""
        print("\n=== Testing Subtask Integration with Task System ===")
        
        if not self.test_data['users'] or not self.test_data['tasks']:
            self.log_result("Subtask Integration Setup", False, "No authenticated users or tasks available")
            return False
        
        user1 = self.test_data['users'][0]
        task = self.test_data['tasks'][0]
        
        try:
            # Create multiple subtasks
            subtasks_data = [
                {
                    "text": "Set up authentication routes",
                    "description": "Implement login, register, and token refresh endpoints",
                    "priority": "high",
                    "estimated_duration": 60
                },
                {
                    "text": "Implement password validation",
                    "description": "Add strong password requirements and validation",
                    "priority": "medium",
                    "estimated_duration": 30
                },
                {
                    "text": "Add JWT middleware",
                    "description": "Create middleware for token validation",
                    "priority": "high",
                    "estimated_duration": 90
                }
            ]
            
            created_subtasks = []
            for subtask_data in subtasks_data:
                response = self.session.post(
                    f"{BACKEND_URL}/tasks/{task['id']}/subtasks",
                    json=subtask_data,
                    headers=user1['headers']
                )
                
                if response.status_code == 200:
                    created_subtasks.append(response.json())
            
            if len(created_subtasks) == 3:
                self.log_result("Multiple Subtasks Creation", True, "Created 3 subtasks successfully")
            else:
                self.log_result("Multiple Subtasks Creation", False, f"Expected 3 subtasks, created {len(created_subtasks)}")
            
            # Test Task Retrieval with Embedded Subtasks
            response = self.session.get(f"{BACKEND_URL}/tasks/{task['id']}", headers=user1['headers'])
            
            if response.status_code == 200:
                updated_task = response.json()
                task_subtasks = updated_task.get('todos', [])
                
                if len(task_subtasks) >= 3:
                    self.log_result("Task with Embedded Subtasks", True, f"Task contains {len(task_subtasks)} subtasks")
                    
                    # Verify subtask data structure
                    first_subtask = task_subtasks[0]
                    required_fields = ['id', 'text', 'completed', 'priority', 'created_at', 'created_by']
                    
                    if all(field in first_subtask for field in required_fields):
                        self.log_result("Subtask Data Structure", True, "Subtasks have all required fields")
                    else:
                        missing = [f for f in required_fields if f not in first_subtask]
                        self.log_result("Subtask Data Structure", False, f"Missing fields: {missing}")
                else:
                    self.log_result("Task with Embedded Subtasks", False, f"Expected >= 3 subtasks, found {len(task_subtasks)}")
            else:
                self.log_result("Task with Embedded Subtasks", False, f"HTTP {response.status_code}")
            
            # Test Subtask Completion Impact on Task Analytics
            if created_subtasks:
                subtask_id = created_subtasks[0]['id']
                
                # Complete a subtask
                response = self.session.put(
                    f"{BACKEND_URL}/tasks/{task['id']}/subtasks/{subtask_id}",
                    json={"completed": True, "actual_duration": 45},
                    headers=user1['headers']
                )
                
                if response.status_code == 200:
                    self.log_result("Subtask Completion", True, "Subtask marked as completed")
                    
                    # Verify task was updated
                    response = self.session.get(f"{BACKEND_URL}/tasks/{task['id']}", headers=user1['headers'])
                    if response.status_code == 200:
                        updated_task = response.json()
                        completed_subtasks = [s for s in updated_task.get('todos', []) if s.get('completed')]
                        
                        if len(completed_subtasks) >= 1:
                            self.log_result("Task Analytics Update", True, "Task analytics reflect subtask completion")
                        else:
                            self.log_result("Task Analytics Update", False, "Task analytics not updated")
                else:
                    self.log_result("Subtask Completion", False, f"HTTP {response.status_code}")
            
            return True
        except Exception as e:
            self.log_result("Subtask Integration", False, f"Error: {str(e)}")
            return False

    def test_subtask_permissions_and_security(self):
        """Test Subtask Permissions and Security"""
        print("\n=== Testing Subtask Permissions and Security ===")
        
        if not self.test_data['users'] or not self.test_data['tasks']:
            self.log_result("Subtask Security Setup", False, "No authenticated users or tasks available")
            return False
        
        user1 = self.test_data['users'][0]
        user2 = self.test_data['users'][1] if len(self.test_data['users']) > 1 else user1
        task = self.test_data['tasks'][0]
        
        try:
            # Create a subtask as user1 (task owner/collaborator)
            subtask_data = {
                "text": "Security testing subtask",
                "description": "Test permissions and access control",
                "assigned_users": [user1['token_data']['user']['id']],
                "priority": "medium"
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/tasks/{task['id']}/subtasks",
                json=subtask_data,
                headers=user1['headers']
            )
            
            if response.status_code == 200:
                subtask = response.json()
                subtask_id = subtask['id']
                self.log_result("Subtask Creation by Authorized User", True, "Task collaborator can create subtasks")
            else:
                self.log_result("Subtask Creation by Authorized User", False, f"HTTP {response.status_code}")
                return False
            
            # Test unauthorized access (no token)
            response = self.session.post(
                f"{BACKEND_URL}/tasks/{task['id']}/subtasks",
                json=subtask_data
            )
            
            if response.status_code in [401, 403]:
                self.log_result("Unauthorized Subtask Creation", True, "Unauthenticated requests properly blocked")
            else:
                self.log_result("Unauthorized Subtask Creation", False, f"Expected 401/403, got {response.status_code}")
            
            # Test access to non-existent task
            fake_task_id = str(uuid.uuid4())
            response = self.session.post(
                f"{BACKEND_URL}/tasks/{fake_task_id}/subtasks",
                json=subtask_data,
                headers=user1['headers']
            )
            
            if response.status_code == 404:
                self.log_result("Non-existent Task Access", True, "Returns 404 for non-existent task")
            else:
                self.log_result("Non-existent Task Access", False, f"Expected 404, got {response.status_code}")
            
            # Test access to non-existent subtask
            fake_subtask_id = str(uuid.uuid4())
            response = self.session.put(
                f"{BACKEND_URL}/tasks/{task['id']}/subtasks/{fake_subtask_id}",
                json={"text": "Updated text"},
                headers=user1['headers']
            )
            
            if response.status_code == 404:
                self.log_result("Non-existent Subtask Access", True, "Returns 404 for non-existent subtask")
            else:
                self.log_result("Non-existent Subtask Access", False, f"Expected 404, got {response.status_code}")
            
            # Test comment permissions
            comment_data = {"comment": "Test comment for permissions"}
            response = self.session.post(
                f"{BACKEND_URL}/tasks/{task['id']}/subtasks/{subtask_id}/comments",
                json=comment_data,
                headers=user1['headers']
            )
            
            if response.status_code == 200:
                comment = response.json()
                comment_id = comment['id']
                self.log_result("Comment Creation by Authorized User", True, "Authorized user can add comments")
                
                # Test comment deletion by unauthorized user (if we have user2)
                if user2 != user1:
                    response = self.session.delete(
                        f"{BACKEND_URL}/tasks/{task['id']}/subtasks/{subtask_id}/comments/{comment_id}",
                        headers=user2['headers']
                    )
                    
                    if response.status_code == 403:
                        self.log_result("Comment Deletion Permission", True, "Non-author cannot delete comment")
                    else:
                        self.log_result("Comment Deletion Permission", False, f"Expected 403, got {response.status_code}")
            else:
                self.log_result("Comment Creation by Authorized User", False, f"HTTP {response.status_code}")
            
            return True
        except Exception as e:
            self.log_result("Subtask Permissions", False, f"Error: {str(e)}")
            return False

    def test_error_handling(self):
        """Test API error handling"""
        print("\n=== Testing Error Handling ===")
        
        try:
            # Test non-existent task
            response = self.session.get(f"{BACKEND_URL}/tasks/non-existent-id")
            if response.status_code == 404:
                self.log_result("404 Error Handling", True, "Properly returns 404 for non-existent task")
            else:
                self.log_result("404 Error Handling", False, f"Expected 404, got {response.status_code}")
            
            # Test non-existent project
            response = self.session.get(f"{BACKEND_URL}/projects/non-existent-id")
            if response.status_code == 404:
                self.log_result("Project 404 Handling", True, "Properly returns 404 for non-existent project")
            else:
                self.log_result("Project 404 Handling", False, f"Expected 404, got {response.status_code}")
            
            return True
        except Exception as e:
            self.log_result("Error Handling", False, f"Error: {str(e)}")
            return False

    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n=== Cleaning Up Test Data ===")
        
        # Delete test tasks
        for task in self.test_data['tasks']:
            try:
                response = self.session.delete(f"{BACKEND_URL}/tasks/{task['id']}")
                if response.status_code == 200:
                    print(f"✅ Deleted task: {task['title']}")
                else:
                    print(f"❌ Failed to delete task: {task['title']}")
            except Exception as e:
                print(f"❌ Error deleting task {task['title']}: {str(e)}")
        
        print(f"Cleanup completed")

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Comprehensive Backend Testing Suite")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 60)
        
        # Test sequence
        tests = [
            self.test_api_connectivity,
            self.test_project_crud,
            self.test_task_crud_with_analytics,
            self.test_analytics_dashboard,
            self.test_project_analytics,
            self.test_performance_metrics,
            self.test_data_relationships,
            self.test_error_handling
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
        print("🏁 FINAL TEST RESULTS")
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
    tester = TaskManagementTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! Backend is working correctly.")
        exit(0)
    else:
        print(f"\n⚠️  {tester.results['failed']} tests failed. Check the issues above.")
        exit(1)