import React, { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from './auth';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Project Tasks Management Component
export const PMProjectTasks = ({ projectId, onClose }) => {
  const [tasks, setTasks] = useState([]);
  const [team, setTeam] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, assigned_to_me, my_tasks
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [selectedTask, setSelectedTask] = useState(null);
  const { user } = useAuth();

  useEffect(() => {
    if (projectId) {
      fetchProjectTasks();
      fetchProjectTeam();
    }
  }, [projectId]);

  const fetchProjectTasks = async () => {
    try {
      const response = await axios.get(`${API}/pm/projects/${projectId}/tasks`);
      setTasks(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching project tasks:", error);
      setLoading(false);
    }
  };

  const fetchProjectTeam = async () => {
    try {
      const response = await axios.get(`${API}/pm/projects/${projectId}/team`);
      setTeam(response.data);
    } catch (error) {
      console.error("Error fetching project team:", error);
    }
  };

  const handleStatusUpdate = async (taskId, newStatus) => {
    try {
      await axios.put(`${API}/tasks/${taskId}`, { status: newStatus });
      // Refresh tasks
      await fetchProjectTasks();
    } catch (error) {
      console.error("Error updating task status:", error);
    }
  };

  const getFilteredTasks = () => {
    let filtered = tasks;

    // Apply filter
    if (filter === 'assigned_to_me') {
      filtered = filtered.filter(task => 
        task.assigned_users.includes(user.id) || 
        task.collaborators.includes(user.id) ||
        task.owner_id === user.id
      );
    } else if (filter === 'my_tasks') {
      filtered = filtered.filter(task => task.owner_id === user.id);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aVal = a[sortBy];
      let bVal = b[sortBy];
      
      if (sortBy === 'priority') {
        const priorityOrder = { urgent: 4, high: 3, medium: 2, low: 1 };
        aVal = priorityOrder[aVal] || 0;
        bVal = priorityOrder[bVal] || 0;
      } else if (sortBy.includes('date')) {
        aVal = new Date(aVal || 0);
        bVal = new Date(bVal || 0);
      }

      if (sortOrder === 'desc') {
        return bVal > aVal ? 1 : -1;
      } else {
        return aVal > bVal ? 1 : -1;
      }
    });

    return filtered;
  };

  const getPriorityIcon = (priority) => {
    switch (priority) {
      case 'urgent': return '🔥';
      case 'high': return '⚡';
      case 'medium': return '📋';
      case 'low': return '📝';
      default: return '📋';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'in_progress': return '#3b82f6';
      case 'blocked': return '#ef4444';
      case 'todo': return '#6b7280';
      default: return '#6b7280';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'completed': return 'Completed';
      case 'in_progress': return 'In Progress';
      case 'blocked': return 'Blocked';
      case 'todo': return 'To Do';
      default: return 'To Do';
    }
  };

  const getAssignedUserNames = (assignedUsers) => {
    const names = assignedUsers.map(userId => {
      const member = team.find(m => m.user.id === userId);
      return member ? member.user.full_name : 'Unknown';
    });
    return names.join(', ');
  };

  const isOverdue = (dueDate) => {
    return dueDate && new Date(dueDate) < new Date() && new Date(dueDate).toDateString() !== new Date().toDateString();
  };

  const filteredTasks = getFilteredTasks();

  if (loading) {
    return (
      <div className="pm-tasks-container">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading project tasks...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="pm-tasks-container">
      <div className="pm-tasks-header">
        <div className="pm-tasks-title">
          <h3>Project Tasks</h3>
          <button className="pm-close-btn" onClick={onClose}>✕</button>
        </div>
        
        <div className="pm-tasks-controls">
          {/* Filter Controls */}
          <div className="pm-filter-group">
            <label className="pm-filter-label">Filter:</label>
            <select 
              className="pm-filter-select"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="all">All Tasks</option>
              <option value="assigned_to_me">Assigned to Me</option>
              <option value="my_tasks">My Tasks</option>
            </select>
          </div>

          {/* Sort Controls */}
          <div className="pm-filter-group">
            <label className="pm-filter-label">Sort by:</label>
            <select 
              className="pm-filter-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="created_at">Created Date</option>
              <option value="due_date">Due Date</option>
              <option value="priority">Priority</option>
              <option value="status">Status</option>
              <option value="title">Title</option>
            </select>
            <button 
              className="pm-sort-order-btn"
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            >
              {sortOrder === 'asc' ? '↑' : '↓'}
            </button>
          </div>

          <div className="pm-tasks-count">
            {filteredTasks.length} task{filteredTasks.length !== 1 ? 's' : ''}
          </div>
        </div>
      </div>

      <div className="pm-tasks-list">
        {filteredTasks.map(task => (
          <div key={task.id} className="pm-task-card">
            <div className="pm-task-header">
              <div className="pm-task-title-section">
                <span className="pm-task-priority">{getPriorityIcon(task.priority)}</span>
                <span className="pm-task-title">{task.title}</span>
                {isOverdue(task.due_date) && (
                  <span className="pm-task-overdue">⏰ OVERDUE</span>
                )}
              </div>
              
              <div className="pm-task-status-section">
                <select
                  className="pm-task-status-select"
                  value={task.status}
                  onChange={(e) => handleStatusUpdate(task.id, e.target.value)}
                  style={{ color: getStatusColor(task.status) }}
                >
                  <option value="todo">To Do</option>
                  <option value="in_progress">In Progress</option>
                  <option value="blocked">Blocked</option>
                  <option value="completed">Completed</option>
                </select>
              </div>
            </div>

            {task.description && (
              <div className="pm-task-description">
                {task.description}
              </div>
            )}

            <div className="pm-task-meta">
              <div className="pm-task-meta-row">
                {task.assigned_users.length > 0 && (
                  <div className="pm-task-meta-item">
                    <span className="pm-meta-label">👥 Assigned:</span>
                    <span className="pm-meta-value">{getAssignedUserNames(task.assigned_users)}</span>
                  </div>
                )}
                
                {task.due_date && (
                  <div className="pm-task-meta-item">
                    <span className="pm-meta-label">📅 Due:</span>
                    <span className={`pm-meta-value ${isOverdue(task.due_date) ? 'overdue' : ''}`}>
                      {new Date(task.due_date).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </div>

              <div className="pm-task-meta-row">
                {task.estimated_duration && (
                  <div className="pm-task-meta-item">
                    <span className="pm-meta-label">⏱️ Estimated:</span>
                    <span className="pm-meta-value">{task.estimated_duration}m</span>
                  </div>
                )}
                
                {task.actual_duration && (
                  <div className="pm-task-meta-item">
                    <span className="pm-meta-label">✓ Actual:</span>
                    <span className="pm-meta-value">{task.actual_duration}m</span>
                  </div>
                )}
              </div>
            </div>

            <div className="pm-task-actions">
              <button 
                className="pm-task-action-btn"
                onClick={() => setSelectedTask(task)}
              >
                View Details
              </button>
              
              {task.status !== 'completed' && (
                <button 
                  className="pm-task-action-btn primary"
                  onClick={() => handleStatusUpdate(task.id, 'completed')}
                >
                  Mark Complete
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {filteredTasks.length === 0 && (
        <div className="pm-empty-state">
          <div className="pm-empty-icon">📋</div>
          <h3>No Tasks Found</h3>
          <p>No tasks match your current filter criteria.</p>
        </div>
      )}

      {/* Task Details Modal */}
      {selectedTask && (
        <PMTaskDetails 
          task={selectedTask}
          team={team}
          onClose={() => setSelectedTask(null)}
          onUpdate={fetchProjectTasks}
        />
      )}
    </div>
  );
};

// Task Details Modal Component
const PMTaskDetails = ({ task, team, onClose, onUpdate }) => {
  const [editing, setEditing] = useState(false);
  const [editData, setEditData] = useState({
    title: task.title,
    description: task.description || '',
    priority: task.priority,
    status: task.status,
    due_date: task.due_date ? new Date(task.due_date).toISOString().slice(0, 16) : '',
    estimated_duration: task.estimated_duration || ''
  });

  const handleSave = async () => {
    try {
      const updateData = {
        ...editData,
        due_date: editData.due_date ? new Date(editData.due_date).toISOString() : null,
        estimated_duration: editData.estimated_duration ? parseInt(editData.estimated_duration) : null
      };

      await axios.put(`${API}/tasks/${task.id}`, updateData);
      setEditing(false);
      onUpdate();
      onClose();
    } catch (error) {
      console.error("Error updating task:", error);
    }
  };

  const getAssignedUserNames = (assignedUsers) => {
    const names = assignedUsers.map(userId => {
      const member = team.find(m => m.user.id === userId);
      return member ? member.user.full_name : 'Unknown';
    });
    return names.join(', ');
  };

  return (
    <div className="pm-modal-overlay">
      <div className="pm-modal-content">
        <div className="pm-modal-header">
          <h3>{editing ? 'Edit Task' : 'Task Details'}</h3>
          <button className="pm-close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="pm-modal-body">
          {editing ? (
            <div className="pm-edit-form">
              <div className="pm-form-group">
                <label className="pm-form-label">Title</label>
                <input
                  type="text"
                  className="pm-form-input"
                  value={editData.title}
                  onChange={(e) => setEditData({...editData, title: e.target.value})}
                />
              </div>

              <div className="pm-form-group">
                <label className="pm-form-label">Description</label>
                <textarea
                  className="pm-form-textarea"
                  value={editData.description}
                  onChange={(e) => setEditData({...editData, description: e.target.value})}
                  rows={3}
                />
              </div>

              <div className="pm-form-row">
                <div className="pm-form-group">
                  <label className="pm-form-label">Priority</label>
                  <select
                    className="pm-form-select"
                    value={editData.priority}
                    onChange={(e) => setEditData({...editData, priority: e.target.value})}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>

                <div className="pm-form-group">
                  <label className="pm-form-label">Status</label>
                  <select
                    className="pm-form-select"
                    value={editData.status}
                    onChange={(e) => setEditData({...editData, status: e.target.value})}
                  >
                    <option value="todo">To Do</option>
                    <option value="in_progress">In Progress</option>
                    <option value="blocked">Blocked</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>
              </div>

              <div className="pm-form-row">
                <div className="pm-form-group">
                  <label className="pm-form-label">Due Date</label>
                  <input
                    type="datetime-local"
                    className="pm-form-input"
                    value={editData.due_date}
                    onChange={(e) => setEditData({...editData, due_date: e.target.value})}
                  />
                </div>

                <div className="pm-form-group">
                  <label className="pm-form-label">Estimated Duration (minutes)</label>
                  <input
                    type="number"
                    className="pm-form-input"
                    value={editData.estimated_duration}
                    onChange={(e) => setEditData({...editData, estimated_duration: e.target.value})}
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="pm-task-details">
              <div className="pm-detail-section">
                <h4 className="pm-detail-title">{task.title}</h4>
                {task.description && (
                  <p className="pm-detail-description">{task.description}</p>
                )}
              </div>

              <div className="pm-detail-meta">
                <div className="pm-detail-item">
                  <span className="pm-detail-label">Priority:</span>
                  <span className="pm-detail-value">{task.priority}</span>
                </div>
                <div className="pm-detail-item">
                  <span className="pm-detail-label">Status:</span>
                  <span className="pm-detail-value">{task.status}</span>
                </div>
                {task.assigned_users.length > 0 && (
                  <div className="pm-detail-item">
                    <span className="pm-detail-label">Assigned to:</span>
                    <span className="pm-detail-value">{getAssignedUserNames(task.assigned_users)}</span>
                  </div>
                )}
                {task.due_date && (
                  <div className="pm-detail-item">
                    <span className="pm-detail-label">Due Date:</span>
                    <span className="pm-detail-value">{new Date(task.due_date).toLocaleString()}</span>
                  </div>
                )}
                {task.estimated_duration && (
                  <div className="pm-detail-item">
                    <span className="pm-detail-label">Estimated Duration:</span>
                    <span className="pm-detail-value">{task.estimated_duration} minutes</span>
                  </div>
                )}
                {task.actual_duration && (
                  <div className="pm-detail-item">
                    <span className="pm-detail-label">Actual Duration:</span>
                    <span className="pm-detail-value">{task.actual_duration} minutes</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="pm-modal-footer">
          {editing ? (
            <>
              <button className="pm-btn-secondary" onClick={() => setEditing(false)}>
                Cancel
              </button>
              <button className="pm-btn-primary" onClick={handleSave}>
                Save Changes
              </button>
            </>
          ) : (
            <button className="pm-btn-primary" onClick={() => setEditing(true)}>
              Edit Task
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default PMProjectTasks;