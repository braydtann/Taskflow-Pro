import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Get auth token from localStorage
const getAuthToken = () => {
  const authData = localStorage.getItem('auth');
  if (authData) {
    const parsed = JSON.parse(authData);
    return parsed.token;
  }
  return null;
};

// Create axios instance with auth headers
const createAuthRequest = () => {
  const token = getAuthToken();
  return {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  };
};

// Subtask Comment Component
const SubtaskComment = ({ comment, onUpdate, onDelete, canEdit }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(comment.comment);

  const handleSave = async () => {
    if (editText.trim() !== comment.comment) {
      await onUpdate(comment.id, editText.trim());
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditText(comment.comment);
    setIsEditing(false);
  };

  return (
    <div className="subtask-comment">
      <div className="comment-header">
        <span className="comment-author">{comment.username}</span>
        <span className="comment-date">
          {new Date(comment.created_at).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })}
        </span>
        {canEdit && (
          <div className="comment-actions">
            <button
              onClick={() => setIsEditing(true)}
              className="comment-action-btn edit"
              title="Edit comment"
            >
              ✏️
            </button>
            <button
              onClick={() => onDelete(comment.id)}
              className="comment-action-btn delete"
              title="Delete comment"
            >
              🗑️
            </button>
          </div>
        )}
      </div>
      
      {isEditing ? (
        <div className="comment-edit">
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            className="comment-edit-input"
            rows={2}
          />
          <div className="comment-edit-actions">
            <button onClick={handleSave} className="btn btn-sm btn-primary">
              Save
            </button>
            <button onClick={handleCancel} className="btn btn-sm btn-secondary">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="comment-text">{comment.comment}</div>
      )}
    </div>
  );
};

// Individual Subtask Component
const SubtaskItem = ({ subtask, taskId, onUpdate, onDelete, users, currentUserId }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [showCommentForm, setShowCommentForm] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [editData, setEditData] = useState({
    text: subtask.text,
    description: subtask.description || '',
    assigned_users: subtask.assigned_users || [],
    priority: subtask.priority || 'medium',
    due_date: subtask.due_date ? new Date(subtask.due_date).toISOString().slice(0, 16) : '',
    estimated_duration: subtask.estimated_duration || ''
  });

  const priorityColors = {
    low: 'priority-low',
    medium: 'priority-medium', 
    high: 'priority-high',
    urgent: 'priority-urgent'
  };

  const handleToggleComplete = async () => {
    try {
      await axios.put(
        `${API}/tasks/${taskId}/subtasks/${subtask.id}`,
        { completed: !subtask.completed },
        createAuthRequest()
      );
      onUpdate();
    } catch (error) {
      console.error('Error updating subtask:', error);
    }
  };

  const handleSaveEdit = async () => {
    try {
      const updateData = {
        ...editData,
        estimated_duration: editData.estimated_duration ? parseInt(editData.estimated_duration) : null,
        due_date: editData.due_date ? new Date(editData.due_date).toISOString() : null
      };
      
      await axios.put(
        `${API}/tasks/${taskId}/subtasks/${subtask.id}`,
        updateData,
        createAuthRequest()
      );
      
      setIsEditing(false);
      onUpdate();
    } catch (error) {
      console.error('Error updating subtask:', error);
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) return;
    
    try {
      await axios.post(
        `${API}/tasks/${taskId}/subtasks/${subtask.id}/comments`,
        { comment: newComment.trim() },
        createAuthRequest()
      );
      
      setNewComment('');
      setShowCommentForm(false);
      onUpdate();
    } catch (error) {
      console.error('Error adding comment:', error);
    }
  };

  const handleUpdateComment = async (commentId, newText) => {
    try {
      await axios.put(
        `${API}/tasks/${taskId}/subtasks/${subtask.id}/comments/${commentId}`,
        { comment: newText },
        createAuthRequest()
      );
      onUpdate();
    } catch (error) {
      console.error('Error updating comment:', error);
    }
  };

  const handleDeleteComment = async (commentId) => {
    if (!window.confirm('Delete this comment?')) return;
    
    try {
      await axios.delete(
        `${API}/tasks/${taskId}/subtasks/${subtask.id}/comments/${commentId}`,
        createAuthRequest()
      );
      onUpdate();
    } catch (error) {
      console.error('Error deleting comment:', error);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Delete this subtask?')) return;
    
    try {
      await axios.delete(
        `${API}/tasks/${taskId}/subtasks/${subtask.id}`,
        createAuthRequest()
      );
      onDelete(subtask.id);
    } catch (error) {
      console.error('Error deleting subtask:', error);
    }
  };

  return (
    <div className={`subtask-item ${subtask.completed ? 'completed' : ''}`}>
      <div className="subtask-main">
        <div className="subtask-checkbox-section">
          <input
            type="checkbox"
            checked={subtask.completed}
            onChange={handleToggleComplete}
            className="subtask-checkbox"
          />
        </div>
        
        <div className="subtask-content">
          <div className="subtask-header">
            <span className={`subtask-text ${subtask.completed ? 'line-through' : ''}`}>
              {subtask.text}
            </span>
            
            <div className="subtask-badges">
              {subtask.priority !== 'medium' && (
                <span className={`priority-badge ${priorityColors[subtask.priority]}`}>
                  {subtask.priority}
                </span>
              )}
              
              {subtask.assigned_usernames && subtask.assigned_usernames.length > 0 && (
                <span className="assigned-badge">
                  👤 {subtask.assigned_usernames.join(', ')}
                </span>
              )}
              
              {subtask.due_date && (
                <span className="due-date-badge">
                  📅 {new Date(subtask.due_date).toLocaleDateString()}
                </span>
              )}
              
              {subtask.estimated_duration && (
                <span className="duration-badge">
                  ⏱️ {subtask.estimated_duration}m
                </span>
              )}
            </div>
            
            <div className="subtask-actions">
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="subtask-action-btn"
                title={isExpanded ? 'Collapse' : 'Expand'}
              >
                {isExpanded ? '🔼' : '🔽'}
              </button>
              <button
                onClick={() => setIsEditing(true)}
                className="subtask-action-btn"
                title="Edit subtask"
              >
                ✏️
              </button>
              <button
                onClick={handleDelete}
                className="subtask-action-btn delete"
                title="Delete subtask"
              >
                🗑️
              </button>
            </div>
          </div>
          
          {subtask.description && (
            <div className="subtask-description">
              {subtask.description}
            </div>
          )}
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="subtask-expanded">
          {/* Comments Section */}
          <div className="subtask-comments-section">
            <div className="comments-header">
              <h4>Comments ({subtask.comments?.length || 0})</h4>
              <button
                onClick={() => setShowCommentForm(!showCommentForm)}
                className="btn btn-sm btn-secondary"
              >
                Add Comment
              </button>
            </div>
            
            {showCommentForm && (
              <div className="comment-form">
                <textarea
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Add a comment..."
                  className="comment-input"
                  rows={2}
                />
                <div className="comment-form-actions">
                  <button onClick={handleAddComment} className="btn btn-sm btn-primary">
                    Add Comment
                  </button>
                  <button 
                    onClick={() => {
                      setShowCommentForm(false);
                      setNewComment('');
                    }} 
                    className="btn btn-sm btn-secondary"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
            
            <div className="comments-list">
              {subtask.comments?.map(comment => (
                <SubtaskComment
                  key={comment.id}
                  comment={comment}
                  onUpdate={handleUpdateComment}
                  onDelete={handleDeleteComment}
                  canEdit={comment.user_id === currentUserId}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Edit Form */}
      {isEditing && (
        <div className="subtask-edit-form">
          <div className="form-group">
            <label>Subtask Title</label>
            <input
              type="text"
              value={editData.text}
              onChange={(e) => setEditData({...editData, text: e.target.value})}
              className="form-input"
            />
          </div>
          
          <div className="form-group">
            <label>Description</label>
            <textarea
              value={editData.description}
              onChange={(e) => setEditData({...editData, description: e.target.value})}
              className="form-textarea"
              rows={2}
            />
          </div>
          
          <div className="form-row">
            <div className="form-group">
              <label>Priority</label>
              <select
                value={editData.priority}
                onChange={(e) => setEditData({...editData, priority: e.target.value})}
                className="form-select"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Estimated Duration (minutes)</label>
              <input
                type="number"
                value={editData.estimated_duration}
                onChange={(e) => setEditData({...editData, estimated_duration: e.target.value})}
                className="form-input"
              />
            </div>
          </div>
          
          <div className="form-group">
            <label>Due Date</label>
            <input
              type="datetime-local"
              value={editData.due_date}
              onChange={(e) => setEditData({...editData, due_date: e.target.value})}
              className="form-input"
            />
          </div>
          
          <div className="form-group">
            <label>Assigned Users</label>
            <select
              multiple
              value={editData.assigned_users}
              onChange={(e) => {
                const selected = Array.from(e.target.selectedOptions, option => option.value);
                setEditData({...editData, assigned_users: selected});
              }}
              className="form-select"
              size={Math.min(users.length, 4)}
            >
              {users.map(user => (
                <option key={user.id} value={user.id}>
                  {user.username} ({user.email})
                </option>
              ))}
            </select>
            <small className="form-help">Hold Ctrl/Cmd to select multiple users</small>
          </div>
          
          <div className="form-actions">
            <button onClick={handleSaveEdit} className="btn btn-primary">
              Save Changes
            </button>
            <button 
              onClick={() => setIsEditing(false)} 
              className="btn btn-secondary"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// Main Subtasks Component
const SubtasksSection = ({ task, onTaskUpdate, users, currentUserId }) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [newSubtask, setNewSubtask] = useState({
    text: '',
    description: '',
    assigned_users: [],
    priority: 'medium',
    due_date: '',
    estimated_duration: ''
  });

  const handleAddSubtask = async () => {
    if (!newSubtask.text.trim()) return;
    
    try {
      const subtaskData = {
        ...newSubtask,
        estimated_duration: newSubtask.estimated_duration ? parseInt(newSubtask.estimated_duration) : null,
        due_date: newSubtask.due_date ? new Date(newSubtask.due_date).toISOString() : null
      };
      
      await axios.post(
        `${API}/tasks/${task.id}/subtasks`,
        subtaskData,
        createAuthRequest()
      );
      
      setNewSubtask({
        text: '',
        description: '',
        assigned_users: [],
        priority: 'medium',
        due_date: '',
        estimated_duration: ''
      });
      setShowAddForm(false);
      onTaskUpdate();
    } catch (error) {
      console.error('Error creating subtask:', error);
    }
  };

  const completedCount = task.todos?.filter(todo => todo.completed).length || 0;
  const totalCount = task.todos?.length || 0;

  return (
    <div className="subtasks-section">
      <div className="subtasks-header">
        <h3 className="subtasks-title">
          Subtasks ({completedCount}/{totalCount})
        </h3>
        <div className="subtasks-progress">
          <div className="progress-bar">
            <div 
              className="progress-fill"
              style={{ width: totalCount > 0 ? `${(completedCount / totalCount) * 100}%` : '0%' }}
            ></div>
          </div>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn btn-sm btn-primary"
        >
          + Add Subtask
        </button>
      </div>

      {/* Add Subtask Form */}
      {showAddForm && (
        <div className="add-subtask-form">
          <div className="form-group">
            <input
              type="text"
              value={newSubtask.text}
              onChange={(e) => setNewSubtask({...newSubtask, text: e.target.value})}
              placeholder="Subtask title..."
              className="form-input"
            />
          </div>
          
          <div className="form-group">
            <textarea
              value={newSubtask.description}
              onChange={(e) => setNewSubtask({...newSubtask, description: e.target.value})}
              placeholder="Description (optional)..."
              className="form-textarea"
              rows={2}
            />
          </div>
          
          <div className="form-row">
            <div className="form-group">
              <select
                value={newSubtask.priority}
                onChange={(e) => setNewSubtask({...newSubtask, priority: e.target.value})}
                className="form-select"
              >
                <option value="low">Low Priority</option>
                <option value="medium">Medium Priority</option>
                <option value="high">High Priority</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
            
            <div className="form-group">
              <input
                type="number"
                value={newSubtask.estimated_duration}
                onChange={(e) => setNewSubtask({...newSubtask, estimated_duration: e.target.value})}
                placeholder="Duration (min)"
                className="form-input"
              />
            </div>
          </div>
          
          <div className="form-group">
            <input
              type="datetime-local"
              value={newSubtask.due_date}
              onChange={(e) => setNewSubtask({...newSubtask, due_date: e.target.value})}
              className="form-input"
            />
          </div>
          
          <div className="form-group">
            <select
              multiple
              value={newSubtask.assigned_users}
              onChange={(e) => {
                const selected = Array.from(e.target.selectedOptions, option => option.value);
                setNewSubtask({...newSubtask, assigned_users: selected});
              }}
              className="form-select"
              size={Math.min(users.length, 3)}
            >
              {users.map(user => (
                <option key={user.id} value={user.id}>
                  {user.username} ({user.email})
                </option>
              ))}
            </select>
            <small className="form-help">Hold Ctrl/Cmd to select multiple users</small>
          </div>
          
          <div className="form-actions">
            <button onClick={handleAddSubtask} className="btn btn-primary">
              Add Subtask
            </button>
            <button 
              onClick={() => setShowAddForm(false)} 
              className="btn btn-secondary"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Subtasks List */}
      <div className="subtasks-list">
        {task.todos?.map(subtask => (
          <SubtaskItem
            key={subtask.id}
            subtask={subtask}
            taskId={task.id}
            onUpdate={onTaskUpdate}
            onDelete={onTaskUpdate}
            users={users}
            currentUserId={currentUserId}
          />
        ))}
        
        {totalCount === 0 && (
          <div className="no-subtasks">
            <p>No subtasks yet. Click "Add Subtask" to get started!</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SubtasksSection;