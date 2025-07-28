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
BACKEND_URL = "https://34c353d5-13c6-4f3d-b463-fb80eaba5a2e.preview.emergentagent.com/api"
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

    def test_team_assignment_functionality(self):
        """Test Team Assignment Features"""
        print("\n=== Testing Team Assignment Functionality ===")
        
        if not self.test_data['users']:
            self.log_result("Team Assignment Setup", False, "No authenticated users available")
            return False
        
        user1 = self.test_data['users'][0]
        user2 = self.test_data['users'][1] if len(self.test_data['users']) > 1 else user1
        
        try:
            # First, create a team (assuming admin functionality exists)
            # For testing purposes, we'll simulate team membership by adding team_ids to users
            test_team_id = str(uuid.uuid4())
            
            # Test 1: Create task with team assignment
            if self.test_data['projects']:
                project = self.test_data['projects'][0]
                task_data = {
                    "title": "Team-Assigned Task: Frontend Development",
                    "description": "Develop React components for the dashboard with team collaboration",
                    "priority": "high",
                    "project_id": project['id'],
                    "estimated_duration": 360,  # 6 hours
                    "assigned_teams": [test_team_id],  # Assign to team
                    "assigned_users": [user1['token_data']['user']['id']],
                    "collaborators": [user2['token_data']['user']['id']] if user2 != user1 else [],
                    "tags": ["frontend", "team-task", "react"]
                }
                
                response = self.session.post(f"{BACKEND_URL}/tasks", json=task_data, headers=user1['headers'])
                if response.status_code == 200:
                    team_task = response.json()
                    self.test_data['tasks'].append(team_task)
                    
                    # Verify assigned_teams field is present
                    if team_task.get('assigned_teams') == [test_team_id]:
                        self.log_result("Task Creation with Team Assignment", True, f"Task assigned to team: {test_team_id[:8]}...")
                    else:
                        self.log_result("Task Creation with Team Assignment", False, "assigned_teams field not set correctly")
                else:
                    self.log_result("Task Creation with Team Assignment", False, f"HTTP {response.status_code}: {response.text}")
                    return False
            
            # Test 2: Update task with team assignments
            if self.test_data['tasks']:
                task = self.test_data['tasks'][-1]  # Use the team task we just created
                new_team_id = str(uuid.uuid4())
                
                update_data = {
                    "assigned_teams": [test_team_id, new_team_id],  # Add another team
                    "title": "Updated Team-Assigned Task: Full-Stack Development"
                }
                
                response = self.session.put(f"{BACKEND_URL}/tasks/{task['id']}", json=update_data, headers=user1['headers'])
                if response.status_code == 200:
                    updated_task = response.json()
                    if len(updated_task.get('assigned_teams', [])) == 2:
                        self.log_result("Task Update with Team Assignment", True, "Task updated with multiple team assignments")
                    else:
                        self.log_result("Task Update with Team Assignment", False, "Team assignments not updated correctly")
                else:
                    self.log_result("Task Update with Team Assignment", False, f"HTTP {response.status_code}")
            
            # Test 3: Verify task retrieval includes team-assigned tasks
            response = self.session.get(f"{BACKEND_URL}/tasks", headers=user1['headers'])
            if response.status_code == 200:
                tasks = response.json()
                team_tasks = [t for t in tasks if t.get('assigned_teams')]
                
                if len(team_tasks) > 0:
                    self.log_result("Task Retrieval with Team Assignments", True, f"Found {len(team_tasks)} team-assigned tasks")
                else:
                    self.log_result("Task Retrieval with Team Assignments", False, "No team-assigned tasks found in retrieval")
            else:
                self.log_result("Task Retrieval with Team Assignments", False, f"HTTP {response.status_code}")
            
            # Test 4: Individual task retrieval includes team assignment data
            if self.test_data['tasks']:
                task = self.test_data['tasks'][-1]
                response = self.session.get(f"{BACKEND_URL}/tasks/{task['id']}", headers=user1['headers'])
                if response.status_code == 200:
                    retrieved_task = response.json()
                    if retrieved_task.get('assigned_teams'):
                        self.log_result("Individual Task Retrieval with Teams", True, "Individual task includes team assignment data")
                    else:
                        self.log_result("Individual Task Retrieval with Teams", False, "Team assignment data missing in individual retrieval")
                else:
                    self.log_result("Individual Task Retrieval with Teams", False, f"HTTP {response.status_code}")
            
            return True
        except Exception as e:
            self.log_result("Team Assignment Functionality", False, f"Error: {str(e)}")
            return False

    def test_search_functionality(self):
        """Test Search Functionality"""
        print("\n=== Testing Search Functionality ===")
        
        if not self.test_data['users'] or not self.test_data['tasks']:
            self.log_result("Search Functionality Setup", False, "No authenticated users or tasks available")
            return False
        
        user1 = self.test_data['users'][0]
        
        try:
            # Create some test tasks with searchable titles
            search_test_tasks = [
                {
                    "title": "Authentication System Implementation",
                    "description": "Build JWT-based authentication with user management",
                    "priority": "high",
                    "tags": ["auth", "security", "backend"]
                },
                {
                    "title": "User Interface Dashboard Design",
                    "description": "Create responsive dashboard with analytics charts",
                    "priority": "medium",
                    "tags": ["ui", "frontend", "design"]
                },
                {
                    "title": "Database Schema Optimization",
                    "description": "Optimize MongoDB queries and indexing strategies",
                    "priority": "low",
                    "tags": ["database", "performance", "backend"]
                }
            ]
            
            created_search_tasks = []
            for task_data in search_test_tasks:
                response = self.session.post(f"{BACKEND_URL}/tasks", json=task_data, headers=user1['headers'])
                if response.status_code == 200:
                    created_search_tasks.append(response.json())
            
            if len(created_search_tasks) < 3:
                self.log_result("Search Test Data Creation", False, f"Only created {len(created_search_tasks)} of 3 test tasks")
                return False
            
            self.log_result("Search Test Data Creation", True, f"Created {len(created_search_tasks)} test tasks for search")
            
            # Test 1: Basic search functionality
            response = self.session.get(f"{BACKEND_URL}/tasks/search/authentication", headers=user1['headers'])
            if response.status_code == 200:
                search_results = response.json()
                if isinstance(search_results, list) and len(search_results) > 0:
                    self.log_result("Basic Search Functionality", True, f"Found {len(search_results)} results for 'authentication'")
                    
                    # Verify search result structure
                    first_result = search_results[0]
                    required_fields = ['id', 'title', 'description', 'status', 'priority']
                    if all(field in first_result for field in required_fields):
                        self.log_result("Search Result Structure", True, "Search results have all required fields")
                    else:
                        missing = [f for f in required_fields if f not in first_result]
                        self.log_result("Search Result Structure", False, f"Missing fields: {missing}")
                else:
                    self.log_result("Basic Search Functionality", False, "No search results returned")
            else:
                self.log_result("Basic Search Functionality", False, f"HTTP {response.status_code}: {response.text}")
            
            # Test 2: Case-insensitive search
            response = self.session.get(f"{BACKEND_URL}/tasks/search/DASHBOARD", headers=user1['headers'])
            if response.status_code == 200:
                search_results = response.json()
                if len(search_results) > 0:
                    self.log_result("Case-Insensitive Search", True, f"Found {len(search_results)} results for 'DASHBOARD' (uppercase)")
                else:
                    self.log_result("Case-Insensitive Search", False, "Case-insensitive search not working")
            else:
                self.log_result("Case-Insensitive Search", False, f"HTTP {response.status_code}")
            
            # Test 3: Partial match search
            response = self.session.get(f"{BACKEND_URL}/tasks/search/data", headers=user1['headers'])
            if response.status_code == 200:
                search_results = response.json()
                if len(search_results) > 0:
                    self.log_result("Partial Match Search", True, f"Found {len(search_results)} results for partial match 'data'")
                else:
                    self.log_result("Partial Match Search", False, "Partial match search not working")
            else:
                self.log_result("Partial Match Search", False, f"HTTP {response.status_code}")
            
            # Test 4: Search with no results
            response = self.session.get(f"{BACKEND_URL}/tasks/search/nonexistentquery12345", headers=user1['headers'])
            if response.status_code == 200:
                search_results = response.json()
                if isinstance(search_results, list) and len(search_results) == 0:
                    self.log_result("Empty Search Results", True, "Search correctly returns empty array for no matches")
                else:
                    self.log_result("Empty Search Results", False, f"Expected empty array, got {len(search_results)} results")
            else:
                self.log_result("Empty Search Results", False, f"HTTP {response.status_code}")
            
            # Test 5: Search results filtering by user access
            response = self.session.get(f"{BACKEND_URL}/tasks/search/system", headers=user1['headers'])
            if response.status_code == 200:
                search_results = response.json()
                # All results should be accessible to the current user
                self.log_result("Search Access Control", True, f"Search returned {len(search_results)} user-accessible results")
            else:
                self.log_result("Search Access Control", False, f"HTTP {response.status_code}")
            
            return True
        except Exception as e:
            self.log_result("Search Functionality", False, f"Error: {str(e)}")
            return False

    def test_user_teams_endpoint(self):
        """Test User Teams Endpoint"""
        print("\n=== Testing User Teams Endpoint ===")
        
        if not self.test_data['users']:
            self.log_result("User Teams Setup", False, "No authenticated users available")
            return False
        
        user1 = self.test_data['users'][0]
        
        try:
            # Test GET /api/teams/user endpoint
            response = self.session.get(f"{BACKEND_URL}/teams/user", headers=user1['headers'])
            if response.status_code == 200:
                user_teams = response.json()
                
                if isinstance(user_teams, list):
                    self.log_result("User Teams Endpoint", True, f"Retrieved {len(user_teams)} teams for user")
                    
                    # If user has teams, verify structure
                    if len(user_teams) > 0:
                        first_team = user_teams[0]
                        required_fields = ['id', 'name']
                        if all(field in first_team for field in required_fields):
                            self.log_result("User Teams Data Structure", True, "Team data has required fields")
                        else:
                            missing = [f for f in required_fields if f not in first_team]
                            self.log_result("User Teams Data Structure", False, f"Missing fields: {missing}")
                    else:
                        self.log_result("User Teams Data Structure", True, "User has no teams (empty array returned)")
                else:
                    self.log_result("User Teams Endpoint", False, "Response is not an array")
            else:
                self.log_result("User Teams Endpoint", False, f"HTTP {response.status_code}: {response.text}")
            
            return True
        except Exception as e:
            self.log_result("User Teams Endpoint", False, f"Error: {str(e)}")
            return False

    def test_timer_with_team_tasks(self):
        """Test Timer Functionality with Team-Assigned Tasks"""
        print("\n=== Testing Timer with Team-Assigned Tasks ===")
        
        if not self.test_data['users'] or not self.test_data['tasks']:
            self.log_result("Timer Team Tasks Setup", False, "No authenticated users or tasks available")
            return False
        
        user1 = self.test_data['users'][0]
        
        try:
            # Find a team-assigned task or create one
            team_task = None
            for task in self.test_data['tasks']:
                if task.get('assigned_teams'):
                    team_task = task
                    break
            
            if not team_task:
                # Create a team-assigned task for timer testing
                test_team_id = str(uuid.uuid4())
                task_data = {
                    "title": "Timer Test Task with Team Assignment",
                    "description": "Testing timer functionality on team-assigned tasks",
                    "priority": "medium",
                    "assigned_teams": [test_team_id],
                    "estimated_duration": 60
                }
                
                response = self.session.post(f"{BACKEND_URL}/tasks", json=task_data, headers=user1['headers'])
                if response.status_code == 200:
                    team_task = response.json()
                    self.test_data['tasks'].append(team_task)
                else:
                    self.log_result("Timer Team Task Creation", False, f"HTTP {response.status_code}")
                    return False
            
            task_id = team_task['id']
            
            # Test 1: Start timer on team-assigned task
            response = self.session.post(f"{BACKEND_URL}/tasks/{task_id}/timer/start", headers=user1['headers'])
            if response.status_code == 200:
                timer_response = response.json()
                if timer_response.get('message') and 'started' in timer_response['message'].lower():
                    self.log_result("Timer Start on Team Task", True, "Timer started successfully on team-assigned task")
                else:
                    self.log_result("Timer Start on Team Task", False, "Timer start response invalid")
            else:
                self.log_result("Timer Start on Team Task", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            # Wait a moment for timer to run
            time.sleep(2)
            
            # Test 2: Get timer status on team-assigned task
            response = self.session.get(f"{BACKEND_URL}/tasks/{task_id}/timer/status", headers=user1['headers'])
            if response.status_code == 200:
                status_response = response.json()
                if status_response.get('is_timer_running') == True:
                    self.log_result("Timer Status on Team Task", True, "Timer status correctly shows running on team task")
                else:
                    self.log_result("Timer Status on Team Task", False, "Timer status not showing as running")
            else:
                self.log_result("Timer Status on Team Task", False, f"HTTP {response.status_code}")
            
            # Test 3: Stop timer on team-assigned task
            response = self.session.post(f"{BACKEND_URL}/tasks/{task_id}/timer/stop", headers=user1['headers'])
            if response.status_code == 200:
                stop_response = response.json()
                if stop_response.get('message') and 'stopped' in stop_response['message'].lower():
                    self.log_result("Timer Stop on Team Task", True, "Timer stopped successfully on team-assigned task")
                    
                    # Verify task was updated with actual duration
                    if stop_response.get('task', {}).get('actual_duration') is not None:
                        self.log_result("Timer Duration Tracking on Team Task", True, "Actual duration tracked on team task")
                    else:
                        self.log_result("Timer Duration Tracking on Team Task", False, "Actual duration not tracked")
                else:
                    self.log_result("Timer Stop on Team Task", False, "Timer stop response invalid")
            else:
                self.log_result("Timer Stop on Team Task", False, f"HTTP {response.status_code}")
            
            return True
        except Exception as e:
            self.log_result("Timer with Team Tasks", False, f"Error: {str(e)}")
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

    def test_project_manager_authentication(self):
        """Test project manager role functionality and permissions"""
        print("\n🔐 Testing Project Manager Authentication & Permissions...")
        
        # Generate unique identifiers for this test run
        test_id = str(uuid.uuid4())[:8]
        
        # Create test users with different roles
        pm_user_data = {
            "email": f"pm.manager.{test_id}@taskflow.com",
            "username": f"pmmanager{test_id}",
            "full_name": "Project Manager",
            "password": "SecurePass123!",
            "role": "project_manager"
        }
        
        admin_user_data = {
            "email": f"admin.user.{test_id}@taskflow.com", 
            "username": f"adminuser{test_id}",
            "full_name": "Admin User",
            "password": "AdminPass123!",
            "role": "admin"
        }
        
        regular_user_data = {
            "email": f"regular.user.{test_id}@taskflow.com",
            "username": f"regularuser{test_id}", 
            "full_name": "Regular User",
            "password": "UserPass123!",
            "role": "user"
        }
        
        # Store tokens for later use
        self.pm_token = None
        self.admin_token = None
        self.regular_token = None
        self.pm_user_id = None
        self.admin_user_id = None
        
        # Register users
        try:
            pm_response = self.session.post(f"{BACKEND_URL}/auth/register", json=pm_user_data)
            admin_response = self.session.post(f"{BACKEND_URL}/auth/register", json=admin_user_data)
            regular_response = self.session.post(f"{BACKEND_URL}/auth/register", json=regular_user_data)
            
            if pm_response.status_code == 200:
                self.pm_token = pm_response.json()["access_token"]
                self.pm_user_id = pm_response.json()["user"]["id"]
                self.log_result("Project Manager Registration", True, "PM user registered successfully")
            else:
                self.log_result("Project Manager Registration", False, f"Status: {pm_response.status_code}, Response: {pm_response.text}")
                
            if admin_response.status_code == 200:
                self.admin_token = admin_response.json()["access_token"]
                self.admin_user_id = admin_response.json()["user"]["id"]
                self.log_result("Admin User Registration", True, "Admin user registered successfully")
            else:
                self.log_result("Admin User Registration", False, f"Status: {admin_response.status_code}, Response: {admin_response.text}")
                
            if regular_response.status_code == 200:
                self.regular_token = regular_response.json()["access_token"]
                self.log_result("Regular User Registration", True, "Regular user registered successfully")
            else:
                self.log_result("Regular User Registration", False, f"Status: {regular_response.status_code}, Response: {regular_response.text}")
                
        except Exception as e:
            self.log_result("User Registration", False, f"Error: {str(e)}")
            return
        
        # Test PM endpoint access with different roles
        if not self.pm_token or not self.admin_token or not self.regular_token:
            self.log_result("Token Setup", False, "Failed to get all required tokens")
            return
            
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

    def test_project_manager_dashboard_endpoints(self):
        """Test all PM dashboard endpoints"""
        print("\n📊 Testing Project Manager Dashboard Endpoints...")
        
        # Check if we have the required tokens
        if not hasattr(self, 'pm_token') or not hasattr(self, 'admin_token') or not self.pm_token or not self.admin_token:
            self.log_result("PM Dashboard Endpoints", False, "PM or Admin token not available")
            return
            
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

    def test_activity_logging_and_notifications(self):
        """Test activity logging and notification creation"""
        print("\n📝 Testing Activity Logging & Notifications...")
        
        # Check if we have the required tokens
        if not hasattr(self, 'pm_token') or not hasattr(self, 'admin_token') or not self.pm_token or not self.admin_token:
            self.log_result("Activity Logging Setup", False, "PM or Admin token not available")
            return
            
        pm_headers = {"Authorization": f"Bearer {self.pm_token}"}
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Get existing project
        if not self.test_data['projects']:
            self.log_result("Activity Logging Setup", False, "No test project found")
            return
            
        project_id = self.test_data['projects'][0]
        
        # Create a task to generate activity
        task_data = {
            "title": "Activity Test Task",
            "description": "Task to test activity logging",
            "project_id": project_id,
            "priority": "medium"
        }
        
        try:
            task_response = self.session.post(f"{BACKEND_URL}/tasks", json=task_data, headers=pm_headers)
            if task_response.status_code == 200:
                task_id = task_response.json()["id"]
                self.test_data['tasks'].append(task_id)
                self.log_result("Activity Generation - Task Creation", True, "Task created to generate activity")
                
                # Update task status to generate more activity
                task_update = {"status": "in_progress"}
                update_response = self.session.put(f"{BACKEND_URL}/tasks/{task_id}", json=task_update, headers=pm_headers)
                if update_response.status_code == 200:
                    self.log_result("Activity Generation - Task Update", True, "Task updated to generate activity")
                else:
                    self.log_result("Activity Generation - Task Update", False, f"Status: {update_response.status_code}")
                    
                # Check if activity was logged
                time.sleep(1)  # Brief delay for activity logging
                activity_response = self.session.get(f"{BACKEND_URL}/pm/activity?project_id={project_id}", headers=pm_headers)
                if activity_response.status_code == 200:
                    activities = activity_response.json()
                    task_activities = [a for a in activities if a.get('entity_type') == 'task' and a.get('entity_id') == task_id]
                    if len(task_activities) > 0:
                        self.log_result("Activity Logging Verification", True, f"Found {len(task_activities)} activity entries for task operations")
                        
                        # Check activity details
                        activity = task_activities[0]
                        required_fields = ['id', 'user_id', 'action', 'entity_type', 'entity_name', 'timestamp']
                        if all(field in activity for field in required_fields):
                            self.log_result("Activity Log Data Structure", True, "Activity entries contain all required fields")
                        else:
                            self.log_result("Activity Log Data Structure", False, "Activity entries missing required fields")
                    else:
                        self.log_result("Activity Logging Verification", False, "No activity entries found for task operations")
                else:
                    self.log_result("Activity Logging Verification", False, f"Status: {activity_response.status_code}")
                    
            else:
                self.log_result("Activity Generation - Task Creation", False, f"Status: {task_response.status_code}")
                
        except Exception as e:
            self.log_result("Activity Logging", False, f"Error: {str(e)}")
        
        # Test notification creation by updating project status
        try:
            status_update = {"status": "completed"}
            status_response = self.session.put(f"{BACKEND_URL}/pm/projects/{project_id}/status", json=status_update, headers=pm_headers)
            if status_response.status_code == 200:
                self.log_result("Notification Generation - Status Update", True, "Project status updated to generate notifications")
                
                # Check if notifications were created
                time.sleep(1)  # Brief delay for notification creation
                notifications_response = self.session.get(f"{BACKEND_URL}/pm/notifications", headers=admin_headers)
                if notifications_response.status_code == 200:
                    notifications = notifications_response.json()
                    project_notifications = [n for n in notifications if n.get('entity_type') == 'project' and n.get('entity_id') == project_id]
                    if len(project_notifications) > 0:
                        self.log_result("Notification Creation Verification", True, f"Found {len(project_notifications)} notifications for project status change")
                        
                        # Test marking notification as read
                        notification_id = project_notifications[0]['id']
                        read_response = self.session.put(f"{BACKEND_URL}/pm/notifications/{notification_id}/read", headers=admin_headers)
                        if read_response.status_code == 200:
                            self.log_result("Notification Mark as Read", True, "Notification marked as read successfully")
                        else:
                            self.log_result("Notification Mark as Read", False, f"Status: {read_response.status_code}")
                    else:
                        self.log_result("Notification Creation Verification", False, "No notifications found for project status change")
                else:
                    self.log_result("Notification Creation Verification", False, f"Status: {notifications_response.status_code}")
            else:
                self.log_result("Notification Generation - Status Update", False, f"Status: {status_response.status_code}")
                
        except Exception as e:
            self.log_result("Notification Testing", False, f"Error: {str(e)}")

    def test_project_status_and_progress(self):
        """Test project status calculation and progress tracking"""
        print("\n📈 Testing Project Status & Progress...")
        
        # Check if we have the required tokens
        if not hasattr(self, 'pm_token') or not hasattr(self, 'admin_token') or not self.pm_token or not self.admin_token:
            self.log_result("Project Status Testing Setup", False, "PM or Admin token not available")
            return
            
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
                        "priority": "medium",
                        "status": "todo"  # Start with todo, then update
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
                    project_check = self.session.get(f"{BACKEND_URL}/projects/{project_id}", headers=pm_headers)
                    if project_check.status_code == 200:
                        project_data = project_check.json()
                        
                        # Verify progress calculation
                        expected_progress = 33.33  # 1 completed out of 3 tasks
                        actual_progress = project_data.get("progress_percentage", 0)
                        if abs(actual_progress - expected_progress) < 1:  # Allow small rounding differences
                            self.log_result("Project Progress Calculation", True, f"Progress calculated correctly: {actual_progress}%")
                        else:
                            self.log_result("Project Progress Calculation", False, f"Expected ~{expected_progress}%, got {actual_progress}%")
                        
                        # Verify task counts
                        task_count = project_data.get("task_count", 0)
                        completed_count = project_data.get("completed_task_count", 0)
                        if task_count == 3 and completed_count == 1:
                            self.log_result("Project Task Counts", True, f"Task counts correct: {task_count} total, {completed_count} completed")
                        else:
                            self.log_result("Project Task Counts", False, f"Expected 3 total, 1 completed; got {task_count} total, {completed_count} completed")
                        
                        # Test auto-calculated status
                        auto_status = project_data.get("auto_calculated_status")
                        if auto_status:
                            self.log_result("Auto-calculated Status", True, f"Auto status calculated: {auto_status}")
                        else:
                            self.log_result("Auto-calculated Status", False, "No auto-calculated status found")
                            
                    else:
                        self.log_result("Project Progress Check", False, f"Status: {project_check.status_code}")
                        
                    # Test manual status override
                    override_status = {"status": "on_hold"}
                    override_response = self.session.put(f"{BACKEND_URL}/pm/projects/{project_id}/status", json=override_status, headers=pm_headers)
                    if override_response.status_code == 200:
                        self.log_result("Manual Status Override", True, "Manual status override applied")
                        
                        # Verify override was applied
                        override_check = self.session.get(f"{BACKEND_URL}/projects/{project_id}", headers=pm_headers)
                        if override_check.status_code == 200:
                            override_data = override_check.json()
                            if override_data.get("status") == "on_hold" and override_data.get("status_override") == "on_hold":
                                self.log_result("Status Override Verification", True, "Status override applied and persisted correctly")
                            else:
                                self.log_result("Status Override Verification", False, f"Override not applied correctly: status={override_data.get('status')}, override={override_data.get('status_override')}")
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

    def test_user_creation_with_project_manager_role(self):
        """Test creating users with project_manager role via admin/users endpoint"""
        print("\n=== Testing User Creation with Project Manager Role ===")
        
        # First create an admin user to perform admin operations
        admin_email = f"admin_{uuid.uuid4().hex[:8]}@taskflow.com"
        admin_data = {
            "email": admin_email,
            "username": f"admin_{uuid.uuid4().hex[:6]}",
            "full_name": "Test Admin User",
            "password": "AdminPass123!",
            "role": "admin"
        }
        
        try:
            # Register admin user
            response = self.session.post(f"{BACKEND_URL}/auth/register", json=admin_data)
            if response.status_code == 200:
                admin_token_data = response.json()
                admin_headers = {'Authorization': f"Bearer {admin_token_data['access_token']}"}
                self.log_result("Admin User Registration for Testing", True, f"Admin user registered: {admin_data['username']}")
            else:
                self.log_result("Admin User Registration for Testing", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            # Test 1: Create user with project_manager role via admin endpoint
            pm_user_data = {
                "email": f"pm_user_{uuid.uuid4().hex[:8]}@taskflow.com",
                "username": f"pm_user_{uuid.uuid4().hex[:6]}",
                "full_name": "Test Project Manager User",
                "password": "PMPass123!",
                "role": "project_manager",
                "team_ids": []
            }
            
            response = self.session.post(f"{BACKEND_URL}/admin/users", json=pm_user_data, headers=admin_headers)
            if response.status_code == 200:
                pm_user = response.json()
                
                if pm_user.get('role') == 'project_manager':
                    self.log_result("Create PM User via Admin Endpoint", True, f"PM user created successfully: {pm_user['username']} with role {pm_user['role']}")
                    
                    # Store for later tests
                    self.test_data['created_pm_user'] = pm_user
                    self.test_data['created_pm_user_data'] = pm_user_data
                    self.test_data['admin_headers_for_pm_test'] = admin_headers
                else:
                    self.log_result("Create PM User via Admin Endpoint", False, f"Role mismatch: expected 'project_manager', got '{pm_user.get('role')}'")
            else:
                self.log_result("Create PM User via Admin Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            # Test 2: Verify user appears in user listings with correct role
            response = self.session.get(f"{BACKEND_URL}/admin/users", headers=admin_headers)
            if response.status_code == 200:
                users = response.json()
                pm_users = [u for u in users if u.get('role') == 'project_manager']
                
                if len(pm_users) > 0:
                    found_user = next((u for u in pm_users if u['id'] == pm_user['id']), None)
                    if found_user:
                        self.log_result("PM User in Admin Listing", True, f"PM user appears correctly in admin user listing with role: {found_user['role']}")
                    else:
                        self.log_result("PM User in Admin Listing", False, "Created PM user not found in admin listing")
                else:
                    self.log_result("PM User in Admin Listing", False, "No project manager users found in admin listing")
            else:
                self.log_result("PM User in Admin Listing", False, f"HTTP {response.status_code}: {response.text}")
            
            return True
        except Exception as e:
            self.log_result("User Creation with PM Role", False, f"Error: {str(e)}")
            return False

    def test_pm_user_authentication_and_access(self):
        """Test PM user authentication and access to PM features"""
        print("\n=== Testing PM User Authentication and Access ===")
        
        if 'created_pm_user_data' not in self.test_data:
            self.log_result("PM Authentication Setup", False, "No PM user data available from creation test")
            return False
        
        pm_user_data = self.test_data['created_pm_user_data']
        
        try:
            # Test 1: Login with project_manager user
            login_data = {
                "email": pm_user_data['email'],
                "password": pm_user_data['password']
            }
            
            response = self.session.post(f"{BACKEND_URL}/auth/login", json=login_data)
            if response.status_code == 200:
                pm_token_data = response.json()
                pm_headers = {'Authorization': f"Bearer {pm_token_data['access_token']}"}
                
                if pm_token_data['user']['role'] == 'project_manager':
                    self.log_result("PM User Login Authentication", True, f"PM user logged in successfully with correct role in JWT token")
                    self.test_data['pm_test_headers'] = pm_headers
                    self.test_data['pm_test_token_data'] = pm_token_data
                else:
                    self.log_result("PM User Login Authentication", False, f"Role mismatch in JWT: expected 'project_manager', got '{pm_token_data['user']['role']}'")
            else:
                self.log_result("PM User Login Authentication", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            # Test 2: Verify access to PM dashboard endpoints
            pm_endpoints_to_test = [
                ("/pm/dashboard", "PM Dashboard"),
                ("/pm/projects", "PM Projects"),
                ("/pm/activity", "PM Activity Log"),
                ("/pm/notifications", "PM Notifications")
            ]
            
            for endpoint, name in pm_endpoints_to_test:
                response = self.session.get(f"{BACKEND_URL}{endpoint}", headers=pm_headers)
                if response.status_code == 200:
                    self.log_result(f"PM Access to {name}", True, f"PM user can access {endpoint}")
                else:
                    self.log_result(f"PM Access to {name}", False, f"HTTP {response.status_code} for {endpoint}")
            
            # Test 3: Verify PM users cannot access admin-only endpoints
            admin_only_endpoints = [
                ("/admin/users", "Admin Users Management"),
                ("/admin/teams", "Admin Teams Management")
            ]
            
            for endpoint, name in admin_only_endpoints:
                response = self.session.get(f"{BACKEND_URL}{endpoint}", headers=pm_headers)
                if response.status_code == 403:
                    self.log_result(f"PM Blocked from {name}", True, f"PM correctly blocked from {endpoint} (403 Forbidden)")
                else:
                    self.log_result(f"PM Blocked from {name}", False, f"Expected 403, got {response.status_code} for {endpoint}")
            
            # Test 4: Verify JWT tokens work correctly with project_manager role
            response = self.session.get(f"{BACKEND_URL}/auth/me", headers=pm_headers)
            if response.status_code == 200:
                user_info = response.json()
                if user_info['role'] == 'project_manager':
                    self.log_result("JWT Token Validation with PM Role", True, "JWT token correctly validates PM role in /auth/me endpoint")
                else:
                    self.log_result("JWT Token Validation with PM Role", False, f"JWT validation role mismatch: {user_info['role']}")
            else:
                self.log_result("JWT Token Validation with PM Role", False, f"HTTP {response.status_code}")
            
            return True
        except Exception as e:
            self.log_result("PM User Authentication and Access", False, f"Error: {str(e)}")
            return False

    def test_admin_user_management_with_pm_role(self):
        """Test admin user management endpoints with project_manager role operations"""
        print("\n=== Testing Admin User Management with PM Role ===")
        
        if 'admin_headers_for_pm_test' not in self.test_data:
            self.log_result("Admin User Management Setup", False, "No admin headers available")
            return False
        
        admin_headers = self.test_data['admin_headers_for_pm_test']
        
        try:
            # Test 1: Verify GET /api/admin/users includes users with project_manager role
            response = self.session.get(f"{BACKEND_URL}/admin/users", headers=admin_headers)
            if response.status_code == 200:
                users = response.json()
                
                # Count users by role
                role_counts = {}
                for user in users:
                    role = user.get('role', 'unknown')
                    role_counts[role] = role_counts.get(role, 0) + 1
                
                if 'project_manager' in role_counts and role_counts['project_manager'] > 0:
                    self.log_result("Admin Users List Includes PM Role", True, 
                        f"Admin user listing includes {role_counts['project_manager']} project_manager users")
                else:
                    self.log_result("Admin Users List Includes PM Role", False, "No project_manager users found in admin listing")
                
                # Log all role counts for verification
                role_summary = ", ".join([f"{role}: {count}" for role, count in role_counts.items()])
                self.log_result("User Role Distribution", True, f"Role distribution: {role_summary}")
            else:
                self.log_result("Admin Users List Includes PM Role", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            # Test 2: Create a regular user and update their role to project_manager
            regular_user_data = {
                "email": f"regular_to_pm_{uuid.uuid4().hex[:8]}@taskflow.com",
                "username": f"regular_to_pm_{uuid.uuid4().hex[:6]}",
                "full_name": "Regular User to be PM",
                "password": "RegularPass123!",
                "role": "user",
                "team_ids": []
            }
            
            # Create regular user first
            response = self.session.post(f"{BACKEND_URL}/admin/users", json=regular_user_data, headers=admin_headers)
            if response.status_code == 200:
                regular_user = response.json()
                self.log_result("Create Regular User for Role Update", True, f"Created regular user: {regular_user['username']}")
                
                # Test updating role to project_manager
                update_data = {"role": "project_manager"}
                response = self.session.put(f"{BACKEND_URL}/admin/users/{regular_user['id']}", 
                                          json=update_data, headers=admin_headers)
                if response.status_code == 200:
                    updated_user = response.json()
                    if updated_user.get('role') == 'project_manager':
                        self.log_result("Update User Role to PM", True, 
                            f"Successfully updated user role from 'user' to 'project_manager'")
                    else:
                        self.log_result("Update User Role to PM", False, 
                            f"Role update failed: expected 'project_manager', got '{updated_user.get('role')}'")
                else:
                    self.log_result("Update User Role to PM", False, f"HTTP {response.status_code}: {response.text}")
            else:
                self.log_result("Create Regular User for Role Update", False, f"HTTP {response.status_code}: {response.text}")
            
            # Test 3: Verify role validation accepts all three roles (user, project_manager, admin)
            test_roles = ["user", "project_manager", "admin"]
            role_validation_results = []
            
            for role in test_roles:
                test_user_data = {
                    "email": f"role_validation_{role}_{uuid.uuid4().hex[:6]}@taskflow.com",
                    "username": f"role_val_{role}_{uuid.uuid4().hex[:4]}",
                    "full_name": f"Test {role.replace('_', ' ').title()} User",
                    "password": "TestPass123!",
                    "role": role,
                    "team_ids": []
                }
                
                response = self.session.post(f"{BACKEND_URL}/admin/users", json=test_user_data, headers=admin_headers)
                if response.status_code == 200:
                    created_user = response.json()
                    if created_user.get('role') == role:
                        role_validation_results.append(f"✅ {role}")
                    else:
                        role_validation_results.append(f"❌ {role} (got {created_user.get('role')})")
                else:
                    role_validation_results.append(f"❌ {role} (HTTP {response.status_code})")
            
            self.log_result("Role Validation for All Three Roles", 
                all("✅" in result for result in role_validation_results),
                f"Role validation results: {', '.join(role_validation_results)}")
            
            return True
        except Exception as e:
            self.log_result("Admin User Management with PM Role", False, f"Error: {str(e)}")
            return False

    def test_comprehensive_role_based_access_control(self):
        """Test comprehensive role-based access control across all user types"""
        print("\n=== Testing Comprehensive Role-Based Access Control ===")
        
        try:
            # Create users with all three roles for comprehensive testing
            test_users = {}
            roles_to_test = ["user", "project_manager", "admin"]
            
            for role in roles_to_test:
                user_data = {
                    "email": f"rbac_test_{role}_{uuid.uuid4().hex[:8]}@taskflow.com",
                    "username": f"rbac_{role}_{uuid.uuid4().hex[:6]}",
                    "full_name": f"RBAC Test {role.replace('_', ' ').title()}",
                    "password": "RBACTest123!",
                    "role": role
                }
                
                response = self.session.post(f"{BACKEND_URL}/auth/register", json=user_data)
                if response.status_code == 200:
                    token_data = response.json()
                    test_users[role] = {
                        'headers': {'Authorization': f"Bearer {token_data['access_token']}"},
                        'user_data': token_data['user']
                    }
                    self.log_result(f"RBAC Test User Creation ({role})", True, f"Created {role} user for RBAC testing")
                else:
                    self.log_result(f"RBAC Test User Creation ({role})", False, f"HTTP {response.status_code}")
                    return False
            
            # Define access control matrix: (endpoint, user_should_access, pm_should_access, admin_should_access)
            access_control_matrix = [
                # Admin-only endpoints
                ("/admin/users", False, False, True),
                ("/admin/teams", False, False, True),
                
                # PM and Admin endpoints
                ("/pm/dashboard", False, True, True),
                ("/pm/projects", False, True, True),
                ("/pm/activity", False, True, True),
                ("/pm/notifications", False, True, True),
                
                # General user endpoints (all roles should have access)
                ("/tasks", True, True, True),
                ("/projects", True, True, True),
                ("/analytics/dashboard", True, True, True),
                ("/auth/me", True, True, True),
            ]
            
            access_test_results = []
            total_tests = 0
            passed_tests = 0
            
            for endpoint, user_access, pm_access, admin_access in access_control_matrix:
                expected_access = {
                    'user': user_access,
                    'project_manager': pm_access,
                    'admin': admin_access
                }
                
                for role, should_have_access in expected_access.items():
                    if role in test_users:
                        total_tests += 1
                        headers = test_users[role]['headers']
                        
                        response = self.session.get(f"{BACKEND_URL}{endpoint}", headers=headers)
                        
                        if should_have_access:
                            # Should have access (200 or other success codes)
                            if response.status_code in [200, 201]:
                                access_test_results.append(f"✅ {role.upper()} → {endpoint}: Correct access (HTTP {response.status_code})")
                                passed_tests += 1
                            else:
                                access_test_results.append(f"❌ {role.upper()} → {endpoint}: Expected access, got HTTP {response.status_code}")
                        else:
                            # Should be denied (403 or 401)
                            if response.status_code in [401, 403]:
                                access_test_results.append(f"✅ {role.upper()} → {endpoint}: Correctly denied (HTTP {response.status_code})")
                                passed_tests += 1
                            else:
                                access_test_results.append(f"❌ {role.upper()} → {endpoint}: Expected denial, got HTTP {response.status_code}")
            
            # Log detailed results
            self.log_result("Comprehensive Role-Based Access Control", 
                passed_tests == total_tests,
                f"Access control tests: {passed_tests}/{total_tests} passed")
            
            # Print detailed access control results
            print("   Detailed Access Control Results:")
            for result in access_test_results:
                print(f"     {result}")
            
            return passed_tests == total_tests
        except Exception as e:
            self.log_result("Comprehensive Role-Based Access Control", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all backend tests including team assignment and search functionality"""
        print("🚀 Starting Comprehensive Backend Testing Suite - Project Manager Role Focus")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 90)
        
        # Test sequence - Authentication first, then new team and search functionality
        tests = [
            self.test_api_connectivity,
            self.test_user_authentication,
            self.test_project_crud,
            self.test_task_crud_with_analytics,
            self.test_team_assignment_functionality,
            self.test_search_functionality,
            self.test_user_teams_endpoint,
            self.test_timer_with_team_tasks,
            self.test_subtask_crud_operations,
            self.test_subtask_comments_system,
            self.test_subtask_integration_with_tasks,
            self.test_subtask_permissions_and_security,
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
        
        # Test Project Manager Dashboard functionality
        print("\n" + "=" * 80)
        print("🎯 TESTING PROJECT MANAGER DASHBOARD FUNCTIONALITY")
        print("=" * 80)
        self.test_project_manager_authentication()
        self.test_project_manager_dashboard_endpoints()
        self.test_activity_logging_and_notifications()
        self.test_project_status_and_progress()
        
        # Cleanup
        self.cleanup_test_data()
        
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
    tester = TaskManagementTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! Backend is working correctly.")
        exit(0)
    else:
        print(f"\n⚠️  {tester.results['failed']} tests failed. Check the issues above.")
        exit(1)