import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from './auth';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Admin Dashboard Component
export const AdminDashboard = () => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    fetchAdminAnalytics();
  }, []);

  const fetchAdminAnalytics = async () => {
    try {
      const response = await axios.get(`${API}/admin/analytics/dashboard`);
      setAnalytics(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching admin analytics:", error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading admin analytics...</p>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="error-container">
        <p>Unable to load admin analytics</p>
        <button onClick={fetchAdminAnalytics} className="retry-button">Retry</button>
      </div>
    );
  }

  const { overview, recent_activity, top_teams, most_active_users } = analytics;

  return (
    <div className="admin-dashboard">
      {/* Admin Hero Section */}
      <div className="admin-hero-section">
        <div className="admin-hero-content">
          <h1 className="admin-hero-title">Welcome to Admin Center, {user?.full_name}!</h1>
          <p className="admin-hero-subtitle">
            Manage users, teams, and monitor system-wide productivity
          </p>
          <div className="admin-hero-stats">
            <div className="admin-hero-stat">
              <div className="stat-number">{overview.total_users}</div>
              <div className="stat-label">Total Users</div>
            </div>
            <div className="admin-hero-stat">
              <div className="stat-number">{overview.total_teams}</div>
              <div className="stat-label">Teams</div>
            </div>
            <div className="admin-hero-stat">
              <div className="stat-number">{overview.completion_rate}%</div>
              <div className="stat-label">System Completion Rate</div>
            </div>
          </div>
        </div>
      </div>

      {/* System Stats Cards */}
      <div className="admin-stats-grid">
        <div className="stats-card stats-card-users">
          <div className="stats-content">
            <div className="stats-number">{overview.total_users}</div>
            <div className="stats-label">Active Users</div>
            <div className="stats-detail">{overview.admin_users} Admins, {overview.regular_users} Users</div>
          </div>
          <div className="stats-icon">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
            </svg>
          </div>
        </div>

        <div className="stats-card stats-card-teams">
          <div className="stats-content">
            <div className="stats-number">{overview.total_teams}</div>
            <div className="stats-label">Active Teams</div>
          </div>
          <div className="stats-icon">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M16 4c0-1.11.89-2 2-2s2 .89 2 2-.89 2-2 2-2-.89-2-2zM4 18v-4h3v7H5v-5H2v-4c0-1.1.9-2 2-2h3c1.1 0 2 .9 2 2v6h-5zm9-2c-1.66 0-3 1.34-3 3 0 1.66 1.34 3 3 3s3-1.34 3-3c0-1.66-1.34-3-3-3z"/>
            </svg>
          </div>
        </div>

        <div className="stats-card stats-card-tasks">
          <div className="stats-content">
            <div className="stats-number">{overview.total_tasks}</div>
            <div className="stats-label">System Tasks</div>
            <div className="stats-detail">{overview.completed_tasks} Completed</div>
          </div>
          <div className="stats-icon">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 2 2h8c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/>
            </svg>
          </div>
        </div>

        <div className="stats-card stats-card-projects">
          <div className="stats-content">
            <div className="stats-number">{overview.total_projects}</div>
            <div className="stats-label">Active Projects</div>
          </div>
          <div className="stats-icon">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
            </svg>
          </div>
        </div>
      </div>

      {/* Analytics Sections */}
      <div className="admin-analytics-grid">
        {/* Top Teams */}
        <div className="admin-analytics-card">
          <h3 className="analytics-card-title">Top Performing Teams</h3>
          <div className="top-teams-list">
            {top_teams.map((team, index) => (
              <div key={team._id || index} className="top-team-item">
                <div className="team-rank">#{index + 1}</div>
                <div className="team-info">
                  <div className="team-name">{team.name}</div>
                  <div className="team-stats">
                    {team.members} members • {team.task_count} tasks
                  </div>
                </div>
                <div className="team-score">{team.task_count}</div>
              </div>
            ))}
            {top_teams.length === 0 && (
              <div className="empty-state">No teams data available</div>
            )}
          </div>
        </div>

        {/* Most Active Users */}
        <div className="admin-analytics-card">
          <h3 className="analytics-card-title">Most Active Users (30 days)</h3>
          <div className="active-users-list">
            {most_active_users.map((userStats, index) => (
              <div key={userStats.user_id} className="active-user-item">
                <div className="user-avatar">
                  {userStats.full_name?.charAt(0)?.toUpperCase() || 'U'}
                </div>
                <div className="user-info">
                  <div className="user-name">{userStats.full_name}</div>
                  <div className="user-username">@{userStats.username}</div>
                </div>
                <div className="user-activity">
                  <div className="completion-count">{userStats.completed_tasks}</div>
                  <div className="completion-label">tasks completed</div>
                </div>
              </div>
            ))}
            {most_active_users.length === 0 && (
              <div className="empty-state">No user activity data available</div>
            )}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="admin-analytics-card">
          <h3 className="analytics-card-title">Recent Activity (7 days)</h3>
          <div className="recent-activity-stats">
            <div className="activity-stat">
              <div className="activity-icon">
                <svg fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM12 5c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
                </svg>
              </div>
              <div className="activity-details">
                <div className="activity-number">{recent_activity.new_users_week}</div>
                <div className="activity-label">New Users</div>
              </div>
            </div>

            <div className="activity-stat">
              <div className="activity-icon">
                <svg fill="currentColor" viewBox="0 0 24 24">
                  <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 2 2h8c1.1 0 2-.9 2-2V8l-6-6z"/>
                </svg>
              </div>
              <div className="activity-details">
                <div className="activity-number">{recent_activity.new_tasks_week}</div>
                <div className="activity-label">New Tasks</div>
              </div>
            </div>

            <div className="activity-stat">
              <div className="activity-icon">
                <svg fill="currentColor" viewBox="0 0 24 24">
                  <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
                </svg>
              </div>
              <div className="activity-details">
                <div className="activity-number">{recent_activity.new_projects_week}</div>
                <div className="activity-label">New Projects</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// User Management Component
export const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/admin/users`);
      setUsers(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching users:", error);
      setLoading(false);
    }
  };

  const handleCreateUser = async (userData) => {
    try {
      await axios.post(`${API}/admin/users`, userData);
      await fetchUsers();
      setShowCreateForm(false);
    } catch (error) {
      console.error("Error creating user:", error);
      throw error;
    }
  };

  const handleUpdateUser = async (userId, userData) => {
    try {
      await axios.put(`${API}/admin/users/${userId}`, userData);
      await fetchUsers();
      setEditingUser(null);
    } catch (error) {
      console.error("Error updating user:", error);
      throw error;
    }
  };

  const handleDeleteUser = async (userId) => {
    if (window.confirm("Are you sure you want to deactivate this user?")) {
      try {
        await axios.delete(`${API}/admin/users/${userId}`);
        await fetchUsers();
      } catch (error) {
        console.error("Error deleting user:", error);
      }
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading users...</p>
      </div>
    );
  }

  return (
    <div className="user-management">
      <div className="management-header">
        <h1 className="management-title">User Management</h1>
        <button
          onClick={() => setShowCreateForm(true)}
          className="btn btn-primary"
        >
          <svg fill="currentColor" viewBox="0 0 24 24" className="btn-icon">
            <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
          </svg>
          Create User
        </button>
      </div>

      <div className="users-table-container">
        <table className="users-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.id} className={!user.is_active ? 'user-inactive' : ''}>
                <td>
                  <div className="user-info">
                    <div className="user-avatar">
                      {user.full_name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div className="user-name">{user.full_name}</div>
                      <div className="user-username">@{user.username}</div>
                    </div>
                  </div>
                </td>
                <td>{user.email}</td>
                <td>
                  <span className={`role-badge role-${user.role}`}>
                    {user.role}
                  </span>
                </td>
                <td>
                  <span className={`status-badge ${user.is_active ? 'status-active' : 'status-inactive'}`}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>{new Date(user.created_at).toLocaleDateString()}</td>
                <td>
                  <div className="user-actions">
                    <button
                      onClick={() => setEditingUser(user)}
                      className="action-btn edit-btn"
                    >
                      Edit
                    </button>
                    {user.is_active && (
                      <button
                        onClick={() => handleDeleteUser(user.id)}
                        className="action-btn delete-btn"
                      >
                        Deactivate
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreateForm && (
        <UserForm
          onSubmit={handleCreateUser}
          onCancel={() => setShowCreateForm(false)}
          title="Create New User"
        />
      )}

      {editingUser && (
        <UserForm
          user={editingUser}
          onSubmit={(userData) => handleUpdateUser(editingUser.id, userData)}
          onCancel={() => setEditingUser(null)}
          title="Edit User"
        />
      )}
    </div>
  );
};

// User Form Component
const UserForm = ({ user, onSubmit, onCancel, title }) => {
  const [formData, setFormData] = useState({
    email: user?.email || '',
    username: user?.username || '',
    full_name: user?.full_name || '',
    role: user?.role || 'user',
    password: '',
    team_ids: user?.team_ids || []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const submitData = { ...formData };
      if (user && !submitData.password) {
        delete submitData.password; // Don't update password if not provided
      }
      await onSubmit(submitData);
    } catch (error) {
      setError(error.response?.data?.detail || 'Operation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-overlay">
      <div className="form-container">
        <div className="form-header">
          <h3 className="form-title">{title}</h3>
          <button onClick={onCancel} className="close-button">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="admin-form">
          {error && (
            <div className="form-error">
              {error}
            </div>
          )}

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input
                type="text"
                className="form-input"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Username</label>
              <input
                type="text"
                className="form-input"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Email</label>
            <input
              type="email"
              className="form-input"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Role</label>
              <select
                className="form-select"
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">
                Password {user ? '(leave blank to keep current)' : ''}
              </label>
              <input
                type="password"
                className="form-input"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required={!user}
                minLength={8}
              />
            </div>
          </div>

          <div className="form-actions">
            <button type="button" onClick={onCancel} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Processing...' : (user ? 'Update User' : 'Create User')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};