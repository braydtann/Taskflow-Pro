import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Team Management Component
export const TeamManagement = () => {
  const [teams, setTeams] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingTeam, setEditingTeam] = useState(null);

  useEffect(() => {
    fetchTeams();
    fetchUsers();
  }, []);

  const fetchTeams = async () => {
    try {
      const response = await axios.get(`${API}/admin/teams`);
      setTeams(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching teams:", error);
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/admin/users`);
      setUsers(response.data.filter(user => user.is_active));
    } catch (error) {
      console.error("Error fetching users:", error);
    }
  };

  const handleCreateTeam = async (teamData) => {
    try {
      await axios.post(`${API}/admin/teams`, teamData);
      await fetchTeams();
      setShowCreateForm(false);
    } catch (error) {
      console.error("Error creating team:", error);
      throw error;
    }
  };

  const handleUpdateTeam = async (teamId, teamData) => {
    try {
      await axios.put(`${API}/admin/teams/${teamId}`, teamData);
      await fetchTeams();
      setEditingTeam(null);
    } catch (error) {
      console.error("Error updating team:", error);
      throw error;
    }
  };

  const handleDeleteTeam = async (teamId) => {
    if (window.confirm("Are you sure you want to delete this team?")) {
      try {
        await axios.delete(`${API}/admin/teams/${teamId}`);
        await fetchTeams();
      } catch (error) {
        console.error("Error deleting team:", error);
      }
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading teams...</p>
      </div>
    );
  }

  return (
    <div className="team-management">
      <div className="management-header">
        <h1 className="management-title">Team Management</h1>
        <button
          onClick={() => setShowCreateForm(true)}
          className="btn btn-primary"
        >
          <svg fill="currentColor" viewBox="0 0 24 24" className="btn-icon">
            <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
          </svg>
          Create Team
        </button>
      </div>

      <div className="teams-grid">
        {teams.map(team => (
          <TeamCard
            key={team.id}
            team={team}
            users={users}
            onEdit={() => setEditingTeam(team)}
            onDelete={() => handleDeleteTeam(team.id)}
          />
        ))}

        {teams.length === 0 && (
          <div className="empty-state-card">
            <div className="empty-state-content">
              <svg fill="currentColor" viewBox="0 0 24 24" className="empty-state-icon">
                <path d="M16 4c0-1.11.89-2 2-2s2 .89 2 2-.89 2-2 2-2-.89-2-2zM4 18v-4h3v7H5v-5H2v-4c0-1.1.9-2 2-2h3c1.1 0 2 .9 2 2v6h-5zm9-2c-1.66 0-3 1.34-3 3 0 1.66 1.34 3 3 3s3-1.34 3-3c0-1.66-1.34-3-3-3z"/>
              </svg>
              <h3>No Teams Yet</h3>
              <p>Create your first team to organize users and projects</p>
              <button
                onClick={() => setShowCreateForm(true)}
                className="btn btn-primary"
              >
                Create Team
              </button>
            </div>
          </div>
        )}
      </div>

      {showCreateForm && (
        <TeamForm
          users={users}
          onSubmit={handleCreateTeam}
          onCancel={() => setShowCreateForm(false)}
          title="Create New Team"
        />
      )}

      {editingTeam && (
        <TeamForm
          team={editingTeam}
          users={users}
          onSubmit={(teamData) => handleUpdateTeam(editingTeam.id, teamData)}
          onCancel={() => setEditingTeam(null)}
          title="Edit Team"
        />
      )}
    </div>
  );
};

// Team Card Component
const TeamCard = ({ team, users, onEdit, onDelete }) => {
  const getTeamLead = () => {
    return users.find(user => user.id === team.team_lead_id);
  };

  const getTeamMembers = () => {
    return users.filter(user => team.members.includes(user.id));
  };

  const teamLead = getTeamLead();
  const teamMembers = getTeamMembers();

  return (
    <div className="team-card">
      <div className="team-card-header">
        <div className="team-info">
          <h3 className="team-name">{team.name}</h3>
          {team.description && (
            <p className="team-description">{team.description}</p>
          )}
        </div>
        <div className="team-actions">
          <button onClick={onEdit} className="action-btn edit-btn">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z"/>
            </svg>
          </button>
          <button onClick={onDelete} className="action-btn delete-btn">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12z"/>
            </svg>
          </button>
        </div>
      </div>

      <div className="team-stats">
        <div className="team-stat">
          <div className="stat-icon">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
            </svg>
          </div>
          <div className="stat-content">
            <div className="stat-number">{team.members.length}</div>
            <div className="stat-label">Members</div>
          </div>
        </div>

        <div className="team-stat">
          <div className="stat-icon">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
            </svg>
          </div>
          <div className="stat-content">
            <div className="stat-number">{team.projects?.length || 0}</div>
            <div className="stat-label">Projects</div>
          </div>
        </div>
      </div>

      {teamLead && (
        <div className="team-lead-section">
          <div className="section-title">Team Lead</div>
          <div className="team-member-item">
            <div className="member-avatar">
              {teamLead.full_name.charAt(0).toUpperCase()}
            </div>
            <div className="member-info">
              <div className="member-name">{teamLead.full_name}</div>
              <div className="member-username">@{teamLead.username}</div>
            </div>
            <div className="member-role-badge">Lead</div>
          </div>
        </div>
      )}

      {teamMembers.length > 0 && (
        <div className="team-members-section">
          <div className="section-title">Members ({teamMembers.length})</div>
          <div className="team-members-list">
            {teamMembers.slice(0, 3).map(member => (
              <div key={member.id} className="team-member-avatar" title={member.full_name}>
                {member.full_name.charAt(0).toUpperCase()}
              </div>
            ))}
            {teamMembers.length > 3 && (
              <div className="team-member-avatar more" title={`+${teamMembers.length - 3} more members`}>
                +{teamMembers.length - 3}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="team-meta">
        <div className="created-date">
          Created {new Date(team.created_at).toLocaleDateString()}
        </div>
      </div>
    </div>
  );
};

// Team Form Component
const TeamForm = ({ team, users, onSubmit, onCancel, title }) => {
  const [formData, setFormData] = useState({
    name: team?.name || '',
    description: team?.description || '',
    team_lead_id: team?.team_lead_id || '',
    members: team?.members || []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await onSubmit(formData);
    } catch (error) {
      setError(error.response?.data?.detail || 'Operation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleMemberToggle = (userId) => {
    setFormData(prev => ({
      ...prev,
      members: prev.members.includes(userId)
        ? prev.members.filter(id => id !== userId)
        : [...prev.members, userId]
    }));
  };

  return (
    <div className="form-overlay">
      <div className="form-container large">
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

          <div className="form-group">
            <label className="form-label">Team Name</label>
            <input
              type="text"
              className="form-input"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              placeholder="Enter team name"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="form-textarea"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Describe the team's purpose and goals"
              rows={3}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Team Lead</label>
            <select
              className="form-select"
              value={formData.team_lead_id}
              onChange={(e) => setFormData({ ...formData, team_lead_id: e.target.value })}
            >
              <option value="">Select Team Lead (Optional)</option>
              {users.map(user => (
                <option key={user.id} value={user.id}>
                  {user.full_name} (@{user.username})
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Team Members</label>
            <div className="members-selection">
              {users.map(user => (
                <div key={user.id} className="member-option">
                  <label className="member-checkbox-label">
                    <input
                      type="checkbox"
                      checked={formData.members.includes(user.id)}
                      onChange={() => handleMemberToggle(user.id)}
                      className="member-checkbox"
                    />
                    <div className="member-info">
                      <div className="member-avatar">
                        {user.full_name.charAt(0).toUpperCase()}
                      </div>
                      <div className="member-details">
                        <div className="member-name">{user.full_name}</div>
                        <div className="member-username">@{user.username}</div>
                      </div>
                      <div className="member-role">
                        <span className={`role-badge role-${user.role}`}>
                          {user.role}
                        </span>
                      </div>
                    </div>
                  </label>
                </div>
              ))}
            </div>
            
            {formData.members.length > 0 && (
              <div className="selected-members-summary">
                Selected {formData.members.length} member{formData.members.length !== 1 ? 's' : ''}
              </div>
            )}
          </div>

          <div className="form-actions">
            <button type="button" onClick={onCancel} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Processing...' : (team ? 'Update Team' : 'Create Team')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};