import React, { useState, useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import axios from "axios";
import TaskManager from "./components";
import { AuthProvider, useAuth, ProtectedRoute, UserProfile } from "./auth";
import { AdminDashboard, UserManagement, TeamManagement } from "./admin-components";
import { WebSocketProvider, useWebSocketContext } from "./websocket";
import DuckAnimation from "./duck-animation";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Real-time Status Indicator Component
const RealTimeStatus = () => {
  const { isConnected, taskUpdates } = useWebSocketContext();
  const [showUpdates, setShowUpdates] = useState(false);
  
  return (
    <div className="realtime-status">
      <div className="connection-indicator">
        <div className={`connection-dot ${isConnected ? 'connected' : 'disconnected'}`}></div>
        <span className="connection-text">
          {isConnected ? 'Live' : 'Offline'}
        </span>
      </div>
      
      {taskUpdates.length > 0 && (
        <div className="updates-indicator">
          <button 
            className="updates-badge"
            onClick={() => setShowUpdates(!showUpdates)}
            title={`${taskUpdates.length} recent updates`}
          >
            {taskUpdates.length}
          </button>
          
          {showUpdates && (
            <div className="updates-dropdown">
              <div className="updates-header">Recent Activity</div>
              {taskUpdates.slice(0, 5).map((update, index) => (
                <div key={index} className="update-item">
                  <div className="update-action">{update.action}</div>
                  <div className="update-task">{update.task.title}</div>
                  <div className="update-time">
                    {new Date(update.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Navigation Component (Updated with User Auth)
const Navigation = () => {
  const location = useLocation();
  const { user } = useAuth();
  const [showProfile, setShowProfile] = useState(false);
  
  const navItems = [
    { path: "/", label: "Dashboard", icon: "📊" },
    { path: "/tasks", label: "Tasks", icon: "📋" },
    { path: "/projects", label: "Projects", icon: "📁" },
    { path: "/calendar", label: "Calendar", icon: "📅" },
    { path: "/analytics", label: "Analytics", icon: "📈" }
  ];

  // Add admin nav item for admin users
  if (user?.role === 'admin') {
    navItems.push({ path: "/admin", label: "Admin", icon: "⚙️" });
  }

  return (
    <nav className="nav-container">
      <div className="nav-brand">
        <h2 className="nav-title">TaskFlow Pro</h2>
        <div className="user-welcome">
          Welcome back, {user?.full_name?.split(' ')[0] || 'User'}!
        </div>
      </div>
      
      <div className="nav-items">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`nav-item ${location.pathname === item.path ? 'nav-item-active' : 'nav-item-inactive'}`}
          >
            <svg className="nav-icon" fill="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="3"/>
            </svg>
            {item.label}
          </Link>
        ))}
      </div>

      <div className="nav-user">
        <RealTimeStatus />
        <div className="user-profile-container">
          <button 
            className="user-profile-btn"
            onClick={() => setShowProfile(!showProfile)}
          >
            <div className="user-avatar">
              {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <span className="user-name">{user?.username}</span>
            <svg className="dropdown-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M7 10l5 5 5-5z"/>
            </svg>
          </button>
          
          {showProfile && <UserProfile />}
        </div>
      </div>
    </nav>
  );
};

// Dashboard Component (Updated with Personal Analytics)
const Dashboard = () => {
  const [analytics, setAnalytics] = useState(null);
  const [todaysTasks, setTodaysTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    fetchAnalytics();
    fetchTodaysTasks();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const response = await axios.get(`${API}/analytics/dashboard`);
      setAnalytics(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching analytics:", error);
      setLoading(false);
    }
  };

  const fetchTodaysTasks = async () => {
    try {
      const response = await axios.get(`${API}/tasks`);
      const allTasks = response.data;
      
      // Filter tasks for today based on due_date or start_time
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const tomorrow = new Date(today);
      tomorrow.setDate(tomorrow.getDate() + 1);
      
      const todayTasks = allTasks.filter(task => {
        // Check if task has due_date or start_time for today
        const dueDate = task.due_date ? new Date(task.due_date) : null;
        const startTime = task.start_time ? new Date(task.start_time) : null;
        
        // Include tasks due today or starting today, and exclude completed tasks
        return task.status !== 'completed' && (
          (dueDate && dueDate >= today && dueDate < tomorrow) ||
          (startTime && startTime >= today && startTime < tomorrow) ||
          (!dueDate && !startTime && task.status === 'in_progress') // Include active tasks without dates
        );
      });
      
      // Sort by priority (urgent > high > medium > low) and then by time
      const priorityOrder = { urgent: 4, high: 3, medium: 2, low: 1 };
      const sortedTasks = todayTasks.sort((a, b) => {
        // First sort by priority
        const priorityDiff = (priorityOrder[b.priority] || 0) - (priorityOrder[a.priority] || 0);
        if (priorityDiff !== 0) return priorityDiff;
        
        // Then by time (due_date or start_time, earliest first)
        const aTime = new Date(a.due_date || a.start_time || a.created_at);
        const bTime = new Date(b.due_date || b.start_time || b.created_at);
        return aTime - bTime;
      });
      
      // Take top 4 tasks
      setTodaysTasks(sortedTasks.slice(0, 4));
    } catch (error) {
      console.error("Error fetching today's tasks:", error);
      setTodaysTasks([]);
    }
  };

  const handleTaskClick = (taskId) => {
    // Navigate to tasks view and scroll to specific task
    window.location.href = '/tasks';
    // Store the task ID to scroll to it after navigation
    localStorage.setItem('scrollToTaskId', taskId);
  };

  const handleCreateTask = () => {
    // Navigate to tasks view and open create task form
    window.location.href = '/tasks';
    localStorage.setItem('openCreateTaskForm', 'true');
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading your personal analytics...</p>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="error-container">
        <p>Unable to load dashboard analytics</p>
        <button onClick={fetchAnalytics} className="retry-button">Retry</button>
      </div>
    );
  }

  const { overview, productivity_trends } = analytics;

  return (
    <div className="dashboard-container">
      {/* Personalized Hero Section */}
      <div className="hero-section">
        <div className="hero-content">
          <div className="hero-left">
            <h1 className="hero-title">Welcome back, {user?.full_name}!</h1>
            <p className="hero-subtitle">
              Here's your personal productivity overview for today
            </p>
            <div className="hero-stats">
              <div className="hero-stat">
                <div className="stat-number">{overview.total_tasks}</div>
                <div className="stat-label">Total Tasks</div>
              </div>
              <div className="hero-stat">
                <div className="stat-number">{overview.completion_rate}%</div>
                <div className="stat-label">Completion Rate</div>
              </div>
              <div className="hero-stat">
                <div className="stat-number">{overview.active_projects}</div>
                <div className="stat-label">Active Projects</div>
              </div>
            </div>
          </div>
          
          {/* Today's Tasks Panel */}
          <div className="hero-right">
            <div className="todays-tasks-panel">
              <div className="todays-tasks-header">
                <h3 className="todays-tasks-title">📅 Today's Focus</h3>
                <span className="todays-tasks-count">{todaysTasks.length} tasks</span>
              </div>
              
              {todaysTasks.length > 0 ? (
                <ul className="todays-tasks-list">
                  {todaysTasks.map(task => (
                    <li 
                      key={task.id}
                      className="todays-task-item"
                      onClick={() => handleTaskClick(task.id)}
                    >
                      <div className="task-item-content">
                        <div className="task-item-main">
                          <span className="task-item-title">{task.title}</span>
                          <span className={`task-item-priority priority-${task.priority}`}>
                            {task.priority === 'urgent' && '🔥'}
                            {task.priority === 'high' && '⚡'}
                            {task.priority === 'medium' && '📋'}
                            {task.priority === 'low' && '📝'}
                          </span>
                        </div>
                        <div className="task-item-meta">
                          {task.due_date && (
                            <span className="task-item-time">
                              Due {new Date(task.due_date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                            </span>
                          )}
                          {task.start_time && !task.due_date && (
                            <span className="task-item-time">
                              Starts {new Date(task.start_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                            </span>
                          )}
                          <span className={`task-item-status status-${task.status}`}>
                            {task.status.replace('_', ' ')}
                          </span>
                        </div>
                      </div>
                      <div className="task-item-arrow">
                        <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M9 6l6 6-6 6"/>
                        </svg>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="no-tasks-today">
                  <div className="no-tasks-content">
                    <div className="no-tasks-icon">📅</div>
                    <p className="no-tasks-message">No tasks scheduled for today</p>
                    <button 
                      className="create-task-btn"
                      onClick={handleCreateTask}
                    >
                      <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                      </svg>
                      Create Task
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Personal Stats Cards */}
      <div className="stats-grid">
        <div className="stats-card stats-card-total">
          <div className="stats-content">
            <div className="stats-number">{overview.total_tasks}</div>
            <div className="stats-label">Your Tasks</div>
          </div>
          <div className="stats-icon">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm2-7h-1V2h-2v2H8V2H6v2H5c-1.1 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z"/>
            </svg>
          </div>
        </div>

        <div className="stats-card stats-card-completed">
          <div className="stats-content">
            <div className="stats-number">{overview.completed_tasks}</div>
            <div className="stats-label">Completed</div>
          </div>
          <div className="stats-icon">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
            </svg>
          </div>
        </div>

        <div className="stats-card stats-card-progress">
          <div className="stats-content">
            <div className="stats-number">{overview.in_progress_tasks}</div>
            <div className="stats-label">In Progress</div>
          </div>
          <div className="stats-icon">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
          </div>
        </div>

        <div className="stats-card stats-card-overdue">
          <div className="stats-content">
            <div className="stats-number">{overview.overdue_tasks}</div>
            <div className="stats-label">Overdue</div>
          </div>
          <div className="stats-icon">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z"/>
            </svg>
          </div>
        </div>
      </div>

      {/* Personal Performance Chart */}
      <div className="chart-section">
        <div className="chart-container">
          <h3 className="chart-title">Your 7-Day Productivity Trends</h3>
          <div className="chart-content">
            <div className="productivity-chart">
              {productivity_trends.slice(0, 7).reverse().map((day, index) => (
                <div key={index} className="chart-bar-container">
                  <div className="chart-bar">
                    <div 
                      className="chart-bar-fill"
                      style={{ 
                        height: `${Math.max(day.tasks_completed * 20, 10)}px`,
                        backgroundColor: `hsl(${240 + index * 20}, 70%, 60%)`
                      }}
                    ></div>
                  </div>
                  <div className="chart-label">
                    {new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' })}
                  </div>
                  <div className="chart-value">{day.tasks_completed}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Personal Completion Rate */}
        <div className="completion-rate-card">
          <h3 className="chart-title">Your Success Rate</h3>
          <div className="completion-circle">
            <div className="completion-percentage">
              {overview.completion_rate}%
            </div>
          </div>
          <p className="completion-text">
            {overview.completed_tasks} of {overview.total_tasks} tasks completed
          </p>
          <div className="personal-badge">
            🎯 {overview.completion_rate >= 80 ? 'Productivity Master!' : 
                overview.completion_rate >= 60 ? 'On Track!' : 
                'Room for Growth!'}
          </div>
        </div>
      </div>

      {/* Personalized Quick Actions */}
      <div className="quick-actions">
        <h3 className="section-title">Quick Actions</h3>
        <div className="action-grid">
          <Link to="/tasks" className="action-card">
            <div className="action-icon">
              <svg fill="currentColor" viewBox="0 0 24 24">
                <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
              </svg>
            </div>
            <div className="action-content">
              <h4>Create New Task</h4>
              <p>Add a task to your personal workflow</p>
            </div>
          </Link>

          <Link to="/projects" className="action-card">
            <div className="action-icon">
              <svg fill="currentColor" viewBox="0 0 24 24">
                <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
              </svg>
            </div>
            <div className="action-content">
              <h4>Start New Project</h4>
              <p>Organize your tasks into projects</p>
            </div>
          </Link>

          <Link to="/analytics" className="action-card">
            <div className="action-icon">
              <svg fill="currentColor" viewBox="0 0 24 24">
                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
              </svg>
            </div>
            <div className="action-content">
              <h4>View Analytics</h4>
              <p>Deep dive into your performance metrics</p>
            </div>
          </Link>
        </div>
      </div>
      
      {/* Duck Animation - Easter Egg */}
      <DuckAnimation />
    </div>
  );
};

// Analytics Page Component (Updated for Personal Analytics)
const AnalyticsPage = () => {
  const [timeTrackingData, setTimeTrackingData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    fetchTimeTracking();
  }, []);

  const fetchTimeTracking = async () => {
    try {
      const response = await axios.get(`${API}/analytics/time-tracking`);
      setTimeTrackingData(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching time tracking:", error);
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading-container">Loading your personal analytics...</div>;
  }

  return (
    <div className="analytics-page">
      <div className="page-header">
        <h1 className="page-title">{user?.full_name}'s Performance Analytics</h1>
        <p className="page-subtitle">Deep insights into your personal productivity patterns</p>
      </div>

      {timeTrackingData && (
        <div className="analytics-grid">
          <div className="analytics-card">
            <h3 className="card-title">Your Time Distribution by Project</h3>
            <div className="time-distribution">
              {Object.entries(timeTrackingData.time_by_project).map(([project, minutes]) => (
                <div key={project} className="time-item">
                  <div className="time-item-name">{project}</div>
                  <div className="time-item-value">{Math.round(minutes / 60 * 10) / 10}h</div>
                  <div className="time-item-bar">
                    <div 
                      className="time-item-fill"
                      style={{ 
                        width: `${(minutes / Math.max(...Object.values(timeTrackingData.time_by_project))) * 100}%`
                      }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="analytics-card">
            <h3 className="card-title">Your Time Estimation Accuracy</h3>
            <div className="accuracy-display">
              <div className="accuracy-circle">
                <div className="accuracy-percentage">
                  {timeTrackingData.accuracy_percentage.toFixed(1)}%
                </div>
              </div>
              <div className="accuracy-details">
                <div className="accuracy-item">
                  <span>Estimated: {timeTrackingData.total_estimated_hours}h</span>
                </div>
                <div className="accuracy-item">
                  <span>Actual: {timeTrackingData.total_actual_hours}h</span>
                </div>
                <div className="accuracy-badge">
                  {timeTrackingData.accuracy_percentage >= 80 ? '🎯 Excellent Estimation!' :
                   timeTrackingData.accuracy_percentage >= 60 ? '📈 Good Progress!' :
                   '🎯 Room for Improvement!'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Main App Content (Protected)
const AppContent = () => {
  return (
    <div className="app-layout">
      <Navigation />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tasks" element={<TaskManager />} />
          <Route path="/projects" element={<TaskManager initialTab="projects" />} />
          <Route path="/calendar" element={<TaskManager initialTab="calendar" />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/admin" element={<AdminPanel />} />
        </Routes>
      </main>
    </div>
  );
};

// Main App Component
function App() {
  return (
    <div className="App">
      <AuthProvider>
        <WebSocketProvider>
          <BrowserRouter>
            <ProtectedRoute>
              <AppContent />
            </ProtectedRoute>
          </BrowserRouter>
        </WebSocketProvider>
      </AuthProvider>
    </div>
  );
}

// Admin Panel Component
const AdminPanel = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const { user } = useAuth();

  // Check if user is admin
  if (user?.role !== 'admin') {
    return (
      <div className="unauthorized-container">
        <div className="unauthorized-content">
          <h2>Access Denied</h2>
          <p>You don't have permission to access the admin panel.</p>
          <Link to="/" className="btn btn-primary">Back to Dashboard</Link>
        </div>
      </div>
    );
  }

  const adminTabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'users', label: 'Users', icon: '👥' },
    { id: 'teams', label: 'Teams', icon: '🏢' }
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <AdminDashboard />;
      case 'users':
        return <UserManagement />;
      case 'teams':
        return <TeamManagement />;
      default:
        return <AdminDashboard />;
    }
  };

  return (
    <div className="admin-panel">
      <div className="admin-header">
        <h1 className="admin-title">Admin Panel</h1>
        <div className="admin-nav">
          {adminTabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`admin-tab ${activeTab === tab.id ? 'admin-tab-active' : ''}`}
            >
              <span className="admin-tab-icon">{tab.icon}</span>
              <span className="admin-tab-label">{tab.label}</span>
            </button>
          ))}
        </div>
      </div>
      
      <div className="admin-content">
        {renderContent()}
      </div>
    </div>
  );
};

export default App;