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
          <PMOverview overview={overview} analytics={analytics} />
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

// Enhanced Overview Component with Analytics
const PMOverview = ({ overview, analytics }) => {
  const [filter, setFilter] = useState({ project: 'all', team: 'all', agent: 'all' });

  // Chart data preparation functions
  const preparePieChartData = (data) => {
    return Object.entries(data).map(([key, value]) => ({ name: key, value: value }));
  };

  const prepareBarChartData = (data) => {
    return Object.entries(data).map(([key, value]) => ({ 
      name: key, 
      total: value.total,
      completed: value.completed,
      in_progress: value.in_progress,
      todo: value.todo 
    }));
  };

  const colors = ['#8B5CF6', '#A855F7', '#C084FC', '#D8B4FE', '#E9D5FF'];

  return (
    <div className="pm-overview">
      {/* Enhanced Key Metrics Grid */}
      <div className="pm-stats-grid-enhanced">
        <div className="pm-stats-card assigned-to-me">
          <div className="pm-stats-icon">👤</div>
          <div className="pm-stats-content">
            <div className="pm-stats-number">{overview.tasks_assigned_to_me || 0}</div>
            <div className="pm-stats-label">Tasks Assigned to Me</div>
          </div>
        </div>

        <div className="pm-stats-card scheduled-week">
          <div className="pm-stats-icon">📅</div>
          <div className="pm-stats-content">
            <div className="pm-stats-number">{overview.tasks_scheduled_this_week || 0}</div>
            <div className="pm-stats-label">Tasks Scheduled This Week</div>
          </div>
        </div>

        <div className="pm-stats-card hours-scheduled">
          <div className="pm-stats-icon">⏰</div>
          <div className="pm-stats-content">
            <div className="pm-stats-number">{overview.task_hours_scheduled_this_week || 0}h</div>
            <div className="pm-stats-label">Hours Scheduled This Week</div>
          </div>
        </div>

        <div className="pm-stats-card past-deadline">
          <div className="pm-stats-icon">⚠️</div>
          <div className="pm-stats-content">
            <div className="pm-stats-number">{overview.past_deadline_tasks || 0}</div>
            <div className="pm-stats-label">Past Deadline Tasks</div>
          </div>
        </div>

        <div className="pm-stats-card completed-week">
          <div className="pm-stats-icon">✅</div>
          <div className="pm-stats-content">
            <div className="pm-stats-number">{overview.completed_tasks_this_week || 0}</div>
            <div className="pm-stats-label">Completed Tasks This Week</div>
          </div>
        </div>

        <div className="pm-stats-card completed-hours-week">
          <div className="pm-stats-icon">🕐</div>
          <div className="pm-stats-content">
            <div className="pm-stats-number">{overview.completed_task_hours_this_week || 0}h</div>
            <div className="pm-stats-label">Completed Hours This Week</div>
          </div>
        </div>
      </div>

      {/* Team Completion Estimates */}
      {analytics?.team_completion_estimates && Object.keys(analytics.team_completion_estimates).length > 0 && (
        <div className="pm-chart-section">
          <h3 className="pm-section-title">Team Completion Estimates</h3>
          <div className="team-estimates-grid">
            {Object.entries(analytics.team_completion_estimates).map(([teamName, estimate]) => (
              <div key={teamName} className="team-estimate-card">
                <h4 className="team-name">{teamName}</h4>
                <div className="estimate-details">
                  <div className="estimate-item">
                    <span className="estimate-number">{estimate.estimated_days}</span>
                    <span className="estimate-label">Days to Complete</span>
                  </div>
                  <div className="estimate-item">
                    <span className="estimate-number">{estimate.remaining_tasks}</span>
                    <span className="estimate-label">Remaining Tasks</span>
                  </div>
                  <div className="estimate-item">
                    <span className="estimate-number">{estimate.estimated_hours}h</span>
                    <span className="estimate-label">Estimated Hours</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Charts Section */}
      <div className="pm-charts-container">
        {/* Tasks by Project Chart */}
        {analytics?.tasks_by_project && (
          <div className="pm-chart-card">
            <h3 className="pm-chart-title">Tasks by Project</h3>
            <div className="pm-bar-chart">
              {Object.entries(analytics.tasks_by_project).map(([project, data], index) => (
                <div key={project} className="pm-bar-item">
                  <div className="pm-bar-container">
                    <div className="pm-bar-stack">
                      <div 
                        className="pm-bar-segment completed" 
                        style={{ 
                          height: `${data.total > 0 ? (data.completed / data.total) * 100 : 0}%`,
                          backgroundColor: '#10b981'
                        }}
                        title={`Completed: ${data.completed}`}
                      ></div>
                      <div 
                        className="pm-bar-segment in-progress" 
                        style={{ 
                          height: `${data.total > 0 ? (data.in_progress / data.total) * 100 : 0}%`,
                          backgroundColor: '#3b82f6'
                        }}
                        title={`In Progress: ${data.in_progress}`}
                      ></div>
                      <div 
                        className="pm-bar-segment todo" 
                        style={{ 
                          height: `${data.total > 0 ? (data.todo / data.total) * 100 : 0}%`,
                          backgroundColor: '#f59e0b'
                        }}
                        title={`Todo: ${data.todo}`}
                      ></div>
                    </div>
                  </div>
                  <div className="pm-bar-label">{project.substring(0, 10)}...</div>
                  <div className="pm-bar-total">{data.total}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tasks by Team Chart */}
        {analytics?.tasks_by_team && (
          <div className="pm-chart-card">
            <h3 className="pm-chart-title">Tasks by Team</h3>
            <div className="pm-bar-chart">
              {Object.entries(analytics.tasks_by_team).map(([team, data], index) => (
                <div key={team} className="pm-bar-item">
                  <div className="pm-bar-container">
                    <div className="pm-bar-stack">
                      <div 
                        className="pm-bar-segment completed" 
                        style={{ 
                          height: `${data.total > 0 ? (data.completed / data.total) * 100 : 0}%`,
                          backgroundColor: '#10b981'
                        }}
                        title={`Completed: ${data.completed}`}
                      ></div>
                      <div 
                        className="pm-bar-segment in-progress" 
                        style={{ 
                          height: `${data.total > 0 ? (data.in_progress / data.total) * 100 : 0}%`,
                          backgroundColor: '#3b82f6'
                        }}
                        title={`In Progress: ${data.in_progress}`}
                      ></div>
                      <div 
                        className="pm-bar-segment todo" 
                        style={{ 
                          height: `${data.total > 0 ? (data.todo / data.total) * 100 : 0}%`,
                          backgroundColor: '#f59e0b'
                        }}
                        title={`Todo: ${data.todo}`}
                      ></div>
                    </div>
                  </div>
                  <div className="pm-bar-label">{team.substring(0, 10)}...</div>
                  <div className="pm-bar-total">{data.total}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Projects by ETA Pie Chart */}
        {analytics?.projects_by_eta && (
          <div className="pm-chart-card">
            <h3 className="pm-chart-title">Projects by ETA</h3>
            <div className="pm-pie-chart">
              <div className="pie-chart-container">
                {Object.entries(analytics.projects_by_eta).map(([status, count], index) => {
                  const total = Object.values(analytics.projects_by_eta).reduce((a, b) => a + b, 0);
                  const percentage = total > 0 ? (count / total) * 100 : 0;
                  
                  return (
                    <div key={status} className="pie-segment-info">
                      <div 
                        className="pie-color-indicator" 
                        style={{ backgroundColor: colors[index % colors.length] }}
                      ></div>
                      <span className="pie-label">{status}: {count} ({percentage.toFixed(1)}%)</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Tasks by Assignee Chart */}
        {analytics?.tasks_by_assignee && (
          <div className="pm-chart-card full-width">
            <h3 className="pm-chart-title">Tasks by Assignee</h3>
            <div className="assignee-chart-container">
              {Object.entries(analytics.tasks_by_assignee).slice(0, 10).map(([assignee, data]) => (
                <div key={assignee} className="assignee-row">
                  <div className="assignee-info">
                    <div className="assignee-name">{assignee}</div>
                    <div className="assignee-stats">
                      <span className="stat completed">✓ {data.completed}</span>
                      <span className="stat in-progress">⏳ {data.in_progress}</span>
                      <span className="stat todo">📝 {data.todo}</span>
                      {data.overdue > 0 && <span className="stat overdue">⚠️ {data.overdue}</span>}
                    </div>
                  </div>
                  <div className="assignee-progress">
                    <div className="progress-bar-full">
                      <div 
                        className="progress-bar-fill" 
                        style={{ 
                          width: `${data.total > 0 ? (data.completed / data.total) * 100 : 0}%`,
                          backgroundColor: '#10b981'
                        }}
                      ></div>
                    </div>
                    <span className="progress-text">{data.total} total</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Completed Hours Week over Week */}
        {analytics?.completed_hours_weekly && (
          <div className="pm-chart-card full-width">
            <h3 className="pm-chart-title">
              Completed Hours - Week over Week
              <div className="chart-filters">
                <select 
                  value={filter.project} 
                  onChange={(e) => setFilter({...filter, project: e.target.value})}
                  className="chart-filter-select"
                >
                  <option value="all">All Projects</option>
                </select>
                <select 
                  value={filter.team} 
                  onChange={(e) => setFilter({...filter, team: e.target.value})}
                  className="chart-filter-select"
                >
                  <option value="all">All Teams</option>
                </select>
                <select 
                  value={filter.agent} 
                  onChange={(e) => setFilter({...filter, agent: e.target.value})}
                  className="chart-filter-select"
                >
                  <option value="all">All Agents</option>
                </select>
              </div>
            </h3>
            <div className="line-chart-container">
              <div className="line-chart">
                <svg viewBox="0 0 800 300" className="line-chart-svg">
                  <defs>
                    <linearGradient id="lineGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" style={{stopColor: '#8B5CF6', stopOpacity: 0.8}} />
                      <stop offset="100%" style={{stopColor: '#8B5CF6', stopOpacity: 0.1}} />
                    </linearGradient>
                  </defs>
                  
                  {/* Chart area */}
                  <g transform="translate(60, 20)">
                    {/* Grid lines */}
                    {[0, 1, 2, 3, 4].map(i => (
                      <line 
                        key={i} 
                        x1="0" 
                        y1={i * 60} 
                        x2="700" 
                        y2={i * 60} 
                        stroke="#E5E7EB" 
                        strokeWidth="1"
                      />
                    ))}
                    
                    {/* Data points and line */}
                    {analytics.completed_hours_weekly.length > 1 && (
                      <g>
                        {/* Line path */}
                        <path
                          d={`M ${analytics.completed_hours_weekly.map((point, index) => 
                            `${index * (700 / (analytics.completed_hours_weekly.length - 1))},${240 - (point.hours * 4)}`
                          ).join(' L ')}`}
                          fill="none"
                          stroke="#8B5CF6"
                          strokeWidth="3"
                          strokeLinecap="round"
                        />
                        
                        {/* Area fill */}
                        <path
                          d={`M ${analytics.completed_hours_weekly.map((point, index) => 
                            `${index * (700 / (analytics.completed_hours_weekly.length - 1))},${240 - (point.hours * 4)}`
                          ).join(' L ')} L 700,240 L 0,240 Z`}
                          fill="url(#lineGradient)"
                        />
                        
                        {/* Data points */}
                        {analytics.completed_hours_weekly.map((point, index) => (
                          <g key={index}>
                            <circle
                              cx={index * (700 / (analytics.completed_hours_weekly.length - 1))}
                              cy={240 - (point.hours * 4)}
                              r="6"
                              fill="#8B5CF6"
                              stroke="white"
                              strokeWidth="2"
                            />
                            {/* Week labels */}
                            <text
                              x={index * (700 / (analytics.completed_hours_weekly.length - 1))}
                              y="270"
                              textAnchor="middle"
                              fontSize="12"
                              fill="#6B7280"
                            >
                              {point.date}
                            </text>
                          </g>
                        ))}
                      </g>
                    )}
                  </g>
                  
                  {/* Y-axis labels */}
                  <g>
                    {[0, 15, 30, 45, 60].map((value, index) => (
                      <text
                        key={value}
                        x="50"
                        y={260 - (index * 60)}
                        textAnchor="end"
                        fontSize="12"
                        fill="#6B7280"
                      >
                        {value}h
                      </text>
                    ))}
                  </g>
                </svg>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Original project progress for compatibility */}
      <div className="pm-progress-section">
        <h3 className="pm-section-title">Quick Progress Overview</h3>
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