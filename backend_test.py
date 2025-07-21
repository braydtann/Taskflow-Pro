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
            'tasks': []
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
        """Test Project CRUD operations"""
        print("\n=== Testing Project CRUD Operations ===")
        
        # Test Create Project
        project_data = {
            "name": "Analytics Dashboard Project",
            "description": "Building comprehensive analytics dashboard for task management",
            "owner_id": str(uuid.uuid4()),
            "collaborators": [str(uuid.uuid4())],
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        
        try:
            response = self.session.post(f"{BACKEND_URL}/projects", json=project_data)
            if response.status_code == 200:
                project = response.json()
                self.test_data['projects'].append(project)
                self.log_result("Create Project", True, f"Created project: {project['name']}")
                
                # Test Get Project
                response = self.session.get(f"{BACKEND_URL}/projects/{project['id']}")
                if response.status_code == 200:
                    retrieved_project = response.json()
                    if retrieved_project['name'] == project_data['name']:
                        self.log_result("Get Project by ID", True, "Project retrieved successfully")
                    else:
                        self.log_result("Get Project by ID", False, "Retrieved project data mismatch")
                else:
                    self.log_result("Get Project by ID", False, f"HTTP {response.status_code}")
                
                # Test Get All Projects
                response = self.session.get(f"{BACKEND_URL}/projects")
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
        
        if not self.test_data['projects']:
            self.log_result("Task CRUD Setup", False, "No projects available for task creation")
            return False
        
        project = self.test_data['projects'][0]
        
        # Test Create Task
        task_data = {
            "title": "Implement Real-time Analytics Engine",
            "description": "Build comprehensive analytics engine with productivity metrics calculation",
            "priority": "high",
            "project_id": project['id'],
            "estimated_duration": 480,  # 8 hours in minutes
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "owners": [project['owner_id']],
            "collaborators": project['collaborators'],
            "tags": ["analytics", "backend", "high-priority"]
        }
        
        try:
            response = self.session.post(f"{BACKEND_URL}/tasks", json=task_data)
            if response.status_code == 200:
                task = response.json()
                self.test_data['tasks'].append(task)
                
                # Verify project name was set
                if task.get('project_name') == project['name']:
                    self.log_result("Create Task with Project Link", True, f"Task created with project: {task['project_name']}")
                else:
                    self.log_result("Create Task with Project Link", False, "Project name not set correctly")
                
                # Test Get Task
                response = self.session.get(f"{BACKEND_URL}/tasks/{task['id']}")
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
                response = self.session.put(f"{BACKEND_URL}/tasks/{task['id']}", json=update_data)
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
                response = self.session.put(f"{BACKEND_URL}/tasks/{task['id']}", json=complete_data)
                if response.status_code == 200:
                    completed_task = response.json()
                    if completed_task['status'] == 'completed' and completed_task.get('completed_at'):
                        self.log_result("Complete Task with Analytics", True, "Task completed with timestamp")
                    else:
                        self.log_result("Complete Task with Analytics", False, "Completion not tracked properly")
                else:
                    self.log_result("Complete Task with Analytics", False, f"HTTP {response.status_code}")
                
                # Test Get Tasks with Filters
                response = self.session.get(f"{BACKEND_URL}/tasks?project_id={project['id']}")
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
        
        try:
            response = self.session.get(f"{BACKEND_URL}/analytics/dashboard")
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
        
        if not self.test_data['projects']:
            self.log_result("Project Analytics", False, "No projects available for analytics testing")
            return False
        
        project = self.test_data['projects'][0]
        
        try:
            response = self.session.get(f"{BACKEND_URL}/projects/{project['id']}/analytics")
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
        
        if not self.test_data['projects']:
            self.log_result("Performance Metrics Setup", False, "No test data available")
            return False
        
        user_id = self.test_data['projects'][0]['owner_id']
        
        try:
            # Test User Performance Analytics
            response = self.session.get(f"{BACKEND_URL}/analytics/performance/{user_id}?days=7")
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
            response = self.session.get(f"{BACKEND_URL}/analytics/time-tracking")
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
        
        if not self.test_data['projects'] or not self.test_data['tasks']:
            self.log_result("Data Relationships", False, "Insufficient test data")
            return False
        
        project = self.test_data['projects'][0]
        
        try:
            # Get updated project to check task counts
            response = self.session.get(f"{BACKEND_URL}/projects/{project['id']}")
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