import React, { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from './auth';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Project Manager Dashboard Component
export const ProjectManagerDashboard = () => {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('overview'); // overview, projects, team, activity
  const { user } = useAuth();

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await axios.get(`${API}/pm/dashboard`);
      setDashboard(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching PM dashboard data:", error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading Project Manager Dashboard...</p>
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="error-container">
        <p>Unable to load dashboard data</p>
        <button onClick={fetchDashboardData} className="retry-button">Retry</button>
      </div>
    );
  }

  const { overview, projects, team_workload, recent_activities, analytics } = dashboard;

  return (
    <div className="pm-dashboard-container">
      {/* Header */}
      <div className="pm-hero-section">
        <div className="pm-hero-content">
          <h1 className="pm-hero-title">Project Manager Dashboard</h1>
          <p className="pm-hero-subtitle">
            Welcome back, {user?.full_name}! Manage your projects and teams effectively
          </p>
        </div>
        
        {/* Navigation Tabs */}
        <div className="pm-nav-tabs">
          {[
            { id: 'overview', label: 'Overview', icon: '📊' },
            { id: 'projects', label: 'Projects', icon: '📁' },
            { id: 'team', label: 'Team', icon: '👥' },
            { id: 'activity', label: 'Activity', icon: '📋' }
          ].map(tab => (
            <button
              key={tab.id}
              className={`pm-nav-tab ${view === tab.id ? 'active' : ''}`}
              onClick={() => setView(tab.id)}
            >
              <span className="pm-nav-icon">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="pm-main-content">
        {view === 'overview' && (
          <PMOverview overview={overview} />
        )}
        {view === 'projects' && (
          <PMProjects projects={projects} onRefresh={fetchDashboardData} />
        )}
        {view === 'team' && (
          <PMTeam teamWorkload={team_workload} />
        )}
        {view === 'activity' && (
          <PMActivity activities={recent_activities} />
        )}
      </div>
    </div>
  );
};

// Overview Component
const PMOverview = ({ overview }) => {
  return (
    <div className="pm-overview">
      {/* Key Metrics */}
      <div className="pm-stats-grid">
        <div className="pm-stats-card projects-card">
          <div className="pm-stats-content">
            <div className="pm-stats-number">{overview.total_projects}</div>
            <div className="pm-stats-label">Total Projects</div>
          </div>
          <div className="pm-stats-breakdown">
            <span className="pm-stat-item active">Active: {overview.active_projects}</span>
            <span className="pm-stat-item completed">Completed: {overview.completed_projects}</span>
            <span className="pm-stat-item at-risk">At Risk: {overview.at_risk_projects}</span>
          </div>
        </div>

        <div className="pm-stats-card tasks-card">
          <div className="pm-stats-content">
            <div className="pm-stats-number">{overview.total_tasks}</div>
            <div className="pm-stats-label">Total Tasks</div>
          </div>
          <div className="pm-stats-breakdown">
            <span className="pm-stat-item completed">Completed: {overview.completed_tasks}</span>
            <span className="pm-stat-item in-progress">In Progress: {overview.in_progress_tasks}</span>
            <span className="pm-stat-item overdue">Overdue: {overview.overdue_tasks}</span>
          </div>
        </div>

        <div className="pm-stats-card team-card">
          <div className="pm-stats-content">
            <div className="pm-stats-number">{overview.team_size}</div>
            <div className="pm-stats-label">Team Members</div>
          </div>
          <div className="pm-stats-breakdown">
            <span className="pm-stat-item">Across all projects</span>
          </div>
        </div>

        <div className="pm-stats-card alerts-card">
          <div className="pm-stats-content">
            <div className="pm-stats-number">{overview.blocked_tasks}</div>
            <div className="pm-stats-label">Blocked Tasks</div>
          </div>
          <div className="pm-stats-breakdown">
            <span className="pm-stat-item blocked">Need attention</span>
          </div>
        </div>
      </div>

      {/* Progress Overview Chart */}
      <div className="pm-progress-section">
        <h3 className="pm-section-title">Project Progress Overview</h3>
        <div className="pm-progress-chart">
          <div className="pm-progress-item">
            <div className="pm-progress-bar">
              <div 
                className="pm-progress-fill completed" 
                style={{ width: `${(overview.completed_projects / overview.total_projects) * 100 || 0}%` }}
              ></div>
            </div>
            <span className="pm-progress-label">Completed Projects</span>
            <span className="pm-progress-value">{overview.completed_projects}/{overview.total_projects}</span>
          </div>
          
          <div className="pm-progress-item">
            <div className="pm-progress-bar">
              <div 
                className="pm-progress-fill completed" 
                style={{ width: `${(overview.completed_tasks / overview.total_tasks) * 100 || 0}%` }}
              ></div>
            </div>
            <span className="pm-progress-label">Completed Tasks</span>
            <span className="pm-progress-value">{overview.completed_tasks}/{overview.total_tasks}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Projects Component
const PMProjects = ({ projects, onRefresh }) => {
  const [viewMode, setViewMode] = useState('grid'); // grid or list
  const [selectedProject, setSelectedProject] = useState(null);

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'active': return '#3b82f6';
      case 'on_hold': return '#f59e0b';
      case 'cancelled': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'completed': return 'Completed';
      case 'active': return 'In Progress';
      case 'on_hold': return 'At Risk';
      case 'cancelled': return 'Cancelled';
      default: return 'Not Started';
    }
  };

  return (
    <div className="pm-projects">
      <div className="pm-projects-header">
        <h3 className="pm-section-title">Project Overview</h3>
        <div className="pm-projects-controls">
          <div className="pm-view-toggle">
            <button 
              className={`pm-toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
            >
              📱 Grid
            </button>
            <button 
              className={`pm-toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
            >
              📋 List
            </button>
          </div>
          <button className="pm-refresh-btn" onClick={onRefresh}>
            🔄 Refresh
          </button>
        </div>
      </div>

      <div className={`pm-projects-container ${viewMode}`}>
        {projects.map(project => (
          <div key={project.id} className="pm-project-card" onClick={() => setSelectedProject(project)}>
            <div className="pm-project-header">
              <div className="pm-project-title">{project.name}</div>
              <div 
                className="pm-project-status"
                style={{ backgroundColor: getStatusColor(project.status) }}
              >
                {getStatusLabel(project.status)}
              </div>
            </div>
            
            <div className="pm-project-progress">
              <div className="pm-progress-bar">
                <div 
                  className="pm-progress-fill"
                  style={{ width: `${project.progress_percentage}%` }}
                ></div>
              </div>
              <span className="pm-progress-text">{Math.round(project.progress_percentage)}% Complete</span>
            </div>
            
            <div className="pm-project-meta">
              <div className="pm-project-tasks">
                <span className="pm-meta-label">Tasks:</span>
                <span className="pm-meta-value">
                  {project.completed_task_count}/{project.task_count}
                </span>
              </div>
              
              {project.end_date && (
                <div className="pm-project-due">
                  <span className="pm-meta-label">Due:</span>
                  <span className="pm-meta-value">
                    {new Date(project.end_date).toLocaleDateString()}
                  </span>
                </div>
              )}
              
              {project.assigned_teams?.length > 0 && (
                <div className="pm-project-teams">
                  <span className="pm-meta-label">Teams:</span>
                  <span className="pm-meta-value">{project.assigned_teams.length}</span>
                </div>
              )}
            </div>
            
            <div className="pm-project-actions">
              <button className="pm-action-btn">View Tasks</button>
              <button className="pm-action-btn">Manage</button>
            </div>
          </div>
        ))}
      </div>
      
      {projects.length === 0 && (
        <div className="pm-empty-state">
          <div className="pm-empty-icon">📁</div>
          <h3>No Projects Found</h3>
          <p>You don't have any projects assigned to manage yet.</p>
        </div>
      )}
    </div>
  );
};

// Team Component
const PMTeam = ({ teamWorkload }) => {
  const workloadArray = Object.values(teamWorkload);

  return (
    <div className="pm-team">
      <h3 className="pm-section-title">Team Workload Overview</h3>
      
      <div className="pm-team-grid">
        {workloadArray.map(member => (
          <div key={member.user.id} className="pm-team-card">
            <div className="pm-team-member-header">
              <div className="pm-team-avatar">
                {member.user.full_name.split(' ').map(n => n[0]).join('').toUpperCase()}
              </div>
              <div className="pm-team-member-info">
                <div className="pm-team-member-name">{member.user.full_name}</div>
                <div className="pm-team-member-role">{member.user.role.replace('_', ' ')}</div>
                <div className={`pm-team-availability ${member.availability}`}>
                  {member.availability === 'available' ? '🟢' : '🔴'} {member.availability}
                </div>
              </div>
            </div>
            
            <div className="pm-team-workload">
              <div className="pm-workload-item">
                <span className="pm-workload-label">Total Tasks:</span>
                <span className="pm-workload-value">{member.tasks.total}</span>
              </div>
              <div className="pm-workload-item">
                <span className="pm-workload-label">Active:</span>
                <span className="pm-workload-value active">{member.tasks.active}</span>
              </div>
              <div className="pm-workload-item">
                <span className="pm-workload-label">Completed:</span>
                <span className="pm-workload-value completed">{member.tasks.completed}</span>
              </div>
              {member.tasks.overdue > 0 && (
                <div className="pm-workload-item">
                  <span className="pm-workload-label">Overdue:</span>
                  <span className="pm-workload-value overdue">{member.tasks.overdue}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {workloadArray.length === 0 && (
        <div className="pm-empty-state">
          <div className="pm-empty-icon">👥</div>
          <h3>No Team Members Found</h3>
          <p>No team members are assigned to your projects yet.</p>
        </div>
      )}
    </div>
  );
};

// Activity Component
const PMActivity = ({ activities }) => {
  const getActionIcon = (action) => {
    switch (action) {
      case 'created': return '➕';
      case 'updated': return '✏️';
      case 'completed': return '✅';
      case 'deleted': return '🗑️';
      case 'status_updated': return '🔄';
      default: return '📋';
    }
  };

  const getEntityIcon = (entityType) => {
    switch (entityType) {
      case 'task': return '✓';
      case 'project': return '📁';
      case 'user': return '👤';
      default: return '📄';
    }
  };

  return (
    <div className="pm-activity">
      <h3 className="pm-section-title">Recent Activity</h3>
      
      <div className="pm-activity-timeline">
        {activities.map(activity => (
          <div key={activity.id} className="pm-activity-item">
            <div className="pm-activity-icon">
              {getActionIcon(activity.action)}
            </div>
            <div className="pm-activity-content">
              <div className="pm-activity-header">
                <span className="pm-activity-action">
                  {getEntityIcon(activity.entity_type)} {activity.action}
                </span>
                <span className="pm-activity-entity">{activity.entity_name}</span>
              </div>
              <div className="pm-activity-time">
                {new Date(activity.timestamp).toLocaleString()}
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {activities.length === 0 && (
        <div className="pm-empty-state">
          <div className="pm-empty-icon">📋</div>
          <h3>No Recent Activity</h3>
          <p>No recent activity to display for your projects.</p>
        </div>
      )}
    </div>
  );
};

export default ProjectManagerDashboard;