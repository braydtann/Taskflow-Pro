import React, { useState, useEffect } from "react";
import axios from "axios";
import { CalendarView, GanttChart, EnhancedKanbanBoard, SmartScheduling } from './advanced-components';
import { TimerControls, TimerSummary } from './timer-components';
import { useWebSocketContext } from './websocket';
import SubtasksSection from './subtask-components';
import { useAuth } from './auth';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Task Form Component
const TaskForm = ({ task, onSubmit, onCancel, projects }) => {
  const [formData, setFormData] = useState({
    title: task?.title || "",
    description: task?.description || "",
    priority: task?.priority || "medium",
    project_id: task?.project_id || "",
    estimated_duration: task?.estimated_duration || "",
    due_date: task?.due_date ? new Date(task.due_date).toISOString().slice(0, 16) : "",
    owners: task?.owners?.join(", ") || "",
    collaborators: task?.collaborators?.join(", ") || "",
    assigned_users: task?.assigned_users?.join(", ") || "",
    assigned_teams: task?.assigned_teams || [],
    tags: task?.tags?.join(", ") || ""
  });

  const [showSmartScheduling, setShowSmartScheduling] = useState(false);
  const [userTeams, setUserTeams] = useState([]);

  // Fetch user teams for dropdown
  useEffect(() => {
    const fetchUserTeams = async () => {
      try {
        const response = await axios.get(`${API}/teams/user`);
        setUserTeams(response.data);
      } catch (error) {
        console.error("Error fetching user teams:", error);
      }
    };
    fetchUserTeams();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    const submitData = {
      ...formData,
      estimated_duration: formData.estimated_duration ? parseInt(formData.estimated_duration) : null,
      due_date: formData.due_date ? new Date(formData.due_date).toISOString() : null,
      owners: formData.owners.split(",").map(s => s.trim()).filter(s => s),
      collaborators: formData.collaborators.split(",").map(s => s.trim()).filter(s => s),
      assigned_users: formData.assigned_users.split(",").map(s => s.trim()).filter(s => s),
      assigned_teams: formData.assigned_teams,
      tags: formData.tags.split(",").map(s => s.trim()).filter(s => s)
    };
    onSubmit(submitData);
  };

  const handleScheduleRecommendation = (scheduledTask) => {
    const submitData = {
      ...formData,
      estimated_duration: scheduledTask.estimated_duration,
      start_time: scheduledTask.start_time,
      end_time: scheduledTask.end_time,
      due_date: scheduledTask.end_time,
      owners: formData.owners.split(",").map(s => s.trim()).filter(s => s),
      collaborators: formData.collaborators.split(",").map(s => s.trim()).filter(s => s),
      assigned_users: formData.assigned_users.split(",").map(s => s.trim()).filter(s => s),
      assigned_teams: formData.assigned_teams,
      tags: formData.tags.split(",").map(s => s.trim()).filter(s => s)
    };
    onSubmit(submitData);
  };

  const handleTeamToggle = (teamId) => {
    setFormData(prev => ({
      ...prev,
      assigned_teams: prev.assigned_teams.includes(teamId)
        ? prev.assigned_teams.filter(id => id !== teamId)
        : [...prev.assigned_teams, teamId]
    }));
  };

  return (
    <div className="form-overlay">
      <div className="form-container">
        <div className="form-header">
          <h3 className="form-title">{task ? "Edit Task" : "Create New Task"}</h3>
          <button onClick={onCancel} className="close-button">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="task-form">
          <div className="form-group">
            <label className="form-label">Title *</label>
            <input
              type="text"
              className="form-input"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
              placeholder="Enter task title"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="form-textarea"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Describe the task details"
              rows={3}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Priority</label>
              <select
                className="form-select"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Project</label>
              <select
                className="form-select"
                value={formData.project_id}
                onChange={(e) => setFormData({ ...formData, project_id: e.target.value })}
              >
                <option value="">No Project</option>
                {projects.map(project => (
                  <option key={project.id} value={project.id}>{project.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Estimated Duration (minutes)</label>
              <input
                type="number"
                className="form-input"
                value={formData.estimated_duration}
                onChange={(e) => setFormData({ ...formData, estimated_duration: e.target.value })}
                placeholder="60"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Due Date</label>
              <input
                type="datetime-local"
                className="form-input"
                value={formData.due_date}
                onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Owners (comma-separated emails)</label>
            <input
              type="text"
              className="form-input"
              value={formData.owners}
              onChange={(e) => setFormData({ ...formData, owners: e.target.value })}
              placeholder="user1@email.com, user2@email.com"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Assigned Users (comma-separated emails)</label>
            <input
              type="text"
              className="form-input"
              value={formData.assigned_users}
              onChange={(e) => setFormData({ ...formData, assigned_users: e.target.value })}
              placeholder="user1@email.com, user2@email.com"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Collaborators (comma-separated emails)</label>
            <input
              type="text"
              className="form-input"
              value={formData.collaborators}
              onChange={(e) => setFormData({ ...formData, collaborators: e.target.value })}
              placeholder="collaborator1@email.com, collaborator2@email.com"
            />
          </div>

          {/* Team Assignment Section */}
          {userTeams.length > 0 && (
            <div className="form-group">
              <label className="form-label">Assign to Teams</label>
              <div className="team-selection-container">
                {userTeams.map(team => (
                  <div key={team.id} className="team-checkbox-item">
                    <label className="team-checkbox-label">
                      <input
                        type="checkbox"
                        checked={formData.assigned_teams.includes(team.id)}
                        onChange={() => handleTeamToggle(team.id)}
                        className="team-checkbox"
                      />
                      <span className="team-checkbox-text">
                        <span className="team-name">{team.name}</span>
                        <span className="team-member-count">({team.member_count} members)</span>
                      </span>
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Tags (comma-separated)</label>
            <input
              type="text"
              className="form-input"
              value={formData.tags}
              onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              placeholder="urgent, backend, feature"
            />
          </div>

          {/* Smart Scheduling Section */}
          {!task && formData.estimated_duration && (
            <div className="smart-scheduling-section">
              <div className="scheduling-toggle">
                <button
                  type="button"
                  onClick={() => setShowSmartScheduling(!showSmartScheduling)}
                  className="btn btn-secondary"
                >
                  🤖 Smart Scheduling {showSmartScheduling ? '▼' : '▶'}
                </button>
              </div>
              
              {showSmartScheduling && (
                <SmartScheduling
                  task={{ ...formData, estimated_duration: parseInt(formData.estimated_duration) }}
                  existingTasks={[]} // You can pass existing tasks here
                  onScheduleRecommendation={handleScheduleRecommendation}
                />
              )}
            </div>
          )}

          <div className="form-actions">
            <button type="button" onClick={onCancel} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              {task ? "Update Task" : "Create Task"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Project Form Component
const ProjectForm = ({ project, onSubmit, onCancel }) => {
  const [formData, setFormData] = useState({
    name: project?.name || "",
    description: project?.description || "",
    owner_id: project?.owner_id || "user1", // Default user
    collaborators: project?.collaborators?.join(", ") || "",
    start_date: project?.start_date ? new Date(project.start_date).toISOString().slice(0, 16) : "",
    end_date: project?.end_date ? new Date(project.end_date).toISOString().slice(0, 16) : ""
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const submitData = {
      ...formData,
      start_date: formData.start_date ? new Date(formData.start_date).toISOString() : null,
      end_date: formData.end_date ? new Date(formData.end_date).toISOString() : null,
      collaborators: formData.collaborators.split(",").map(s => s.trim()).filter(s => s)
    };
    onSubmit(submitData);
  };

  return (
    <div className="form-overlay">
      <div className="form-container">
        <div className="form-header">
          <h3 className="form-title">{project ? "Edit Project" : "Create New Project"}</h3>
          <button onClick={onCancel} className="close-button">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="task-form">
          <div className="form-group">
            <label className="form-label">Project Name *</label>
            <input
              type="text"
              className="form-input"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              placeholder="Enter project name"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="form-textarea"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Describe the project goals and scope"
              rows={3}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Start Date</label>
              <input
                type="datetime-local"
                className="form-input"
                value={formData.start_date}
                onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">End Date</label>
              <input
                type="datetime-local"
                className="form-input"
                value={formData.end_date}
                onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Collaborators (comma-separated emails)</label>
            <input
              type="text"
              className="form-input"
              value={formData.collaborators}
              onChange={(e) => setFormData({ ...formData, collaborators: e.target.value })}
              placeholder="collaborator1@email.com, collaborator2@email.com"
            />
          </div>

          <div className="form-actions">
            <button type="button" onClick={onCancel} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              {project ? "Update Project" : "Create Project"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Task Card Component (Updated with Timer and Real-time Indicators)
const TaskCard = ({ task, onEdit, onDelete, onStatusChange, onTaskUpdate, recentlyUpdated }) => {
  const [users, setUsers] = useState([]);
  const { user: currentUser } = useAuth();

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('auth') ? JSON.parse(localStorage.getItem('auth')).token : null;
      if (!token) return;

      const response = await axios.get(`${API}/users/search?q=`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setUsers(response.data);
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  };

  const priorityColors = {
    low: "bg-green-100 text-green-800",
    medium: "bg-yellow-100 text-yellow-800",
    high: "bg-orange-100 text-orange-800",
    urgent: "bg-red-100 text-red-800"
  };

  const statusColors = {
    todo: "bg-gray-100 text-gray-800",
    in_progress: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    cancelled: "bg-red-100 text-red-800"
  };

  return (
    <div className={`task-card ${task.is_timer_running ? 'task-card-timer-active' : ''}`} data-task-id={task.id}>
      <div className="task-header">
        <div className="task-title-section">
          <h4 className="task-title">
            {task.title}
            {recentlyUpdated && (
              <span className="task-realtime-indicator updated">
                ✨ Just updated
              </span>
            )}
          </h4>
          <div className="task-badges">
            <span className={`task-badge ${priorityColors[task.priority]}`}>
              {task.priority}
            </span>
            <span className={`task-badge ${statusColors[task.status]}`}>
              {task.status.replace('_', ' ')}
            </span>
          </div>
        </div>
        
        <div className="task-actions">
          <button onClick={() => onEdit(task)} className="action-btn edit-btn">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
            </svg>
          </button>
          <button onClick={() => onDelete(task.id)} className="action-btn delete-btn">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
            </svg>
          </button>
        </div>
      </div>

      {task.description && (
        <p className="task-description">{task.description}</p>
      )}

      {/* Timer Section */}
      <div className="task-timer-section">
        <TimerControls 
          task={task} 
          onTimerUpdate={onTaskUpdate}
          compact={true}
        />
      </div>

      <div className="task-meta">
        {task.project_name && (
          <div className="task-project">
            <svg fill="currentColor" viewBox="0 0 24 24" className="meta-icon">
              <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
            </svg>
            {task.project_name}
          </div>
        )}
        
        {task.estimated_duration && (
          <div className="task-duration">
            <svg fill="currentColor" viewBox="0 0 24 24" className="meta-icon">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
            Est: {task.estimated_duration} min
          </div>
        )}

        {(task.timer_elapsed_seconds > 0 || task.is_timer_running) && (
          <div className="task-actual-duration">
            <svg fill="currentColor" viewBox="0 0 24 24" className="meta-icon">
              <path d="M15 1H9v2h6V1zm-4 13h2V8h-2v6zm8.03-6.61l1.42-1.42c-.43-.51-.9-.99-1.41-1.41l-1.42 1.42A8.962 8.962 0 0012 4c-4.97 0-9 4.03-9 9s4.02 9 9 9 9-4.03 9-9c0-2.11-.74-4.06-1.97-5.61zM12 20c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/>
            </svg>
            Actual: {Math.round((task.timer_elapsed_seconds || 0) / 60)} min
          </div>
        )}

        {task.due_date && (
          <div className="task-due-date">
            <svg fill="currentColor" viewBox="0 0 24 24" className="meta-icon">
              <path d="M9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm2-7h-1V2h-2v2H8V2H6v2H5c-1.1 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z"/>
            </svg>
            {new Date(task.due_date).toLocaleDateString()}
          </div>
        )}
      </div>

      {(task.assigned_users?.length > 0 || task.collaborators?.length > 0) && (
        <div className="task-people">
          {task.assigned_users?.length > 0 && (
            <div className="people-section">
              <span className="people-label">Assigned:</span>
              <span className="people-list">{task.assigned_users.join(", ")}</span>
            </div>
          )}
          {task.collaborators?.length > 0 && (
            <div className="people-section">
              <span className="people-label">Collaborators:</span>
              <span className="people-list">{task.collaborators.join(", ")}</span>
            </div>
          )}
        </div>
      )}

      {/* Subtasks Section */}
      <SubtasksSection 
        task={task}
        onTaskUpdate={onTaskUpdate}
        users={users}
        currentUserId={currentUser?.id}
      />

      <div className="task-status-controls">
        <select
          value={task.status}
          onChange={(e) => onStatusChange(task.id, e.target.value)}
          className="status-select"
        >
          <option value="todo">To Do</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>
    </div>
  );
};

// Kanban Board Component
const KanbanBoard = ({ tasks, onTaskUpdate, onTaskDelete, projects, selectedProject }) => {
  const filteredTasks = selectedProject 
    ? tasks.filter(task => task.project_id === selectedProject)
    : tasks;

  const columns = [
    { id: "todo", title: "To Do", status: "todo" },
    { id: "in_progress", title: "In Progress", status: "in_progress" },
    { id: "completed", title: "Completed", status: "completed" }
  ];

  return (
    <div className="kanban-board">
      {columns.map(column => (
        <div key={column.id} className="kanban-column">
          <div className="kanban-header">
            <h3 className="kanban-title">{column.title}</h3>
            <span className="task-count">
              {filteredTasks.filter(task => task.status === column.status).length}
            </span>
          </div>
          
          <div className="kanban-tasks">
            {filteredTasks
              .filter(task => task.status === column.status)
              .map(task => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onEdit={() => {}}
                  onDelete={onTaskDelete}
                  onStatusChange={onTaskUpdate}
                />
              ))}
          </div>
        </div>
      ))}
    </div>
  );
};

// Main Task Manager Component
const TaskManager = ({ initialTab = "tasks" }) => {
  const [activeTab, setActiveTab] = useState(initialTab);
  const [tasks, setTasks] = useState([]);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState("");
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [showProjectForm, setShowProjectForm] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [editingProject, setEditingProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recentlyUpdatedTasks, setRecentlyUpdatedTasks] = useState(new Set());

  // WebSocket context for real-time updates
  const { lastMessage, isConnected } = useWebSocketContext();

  useEffect(() => {
    fetchTasks();
    fetchProjects();
    
    // Handle navigation from dashboard
    handleDashboardNavigation();
  }, []);

  // Handle navigation from dashboard (when user clicks on today's tasks)
  const handleDashboardNavigation = () => {
    // Check if we need to scroll to a specific task
    const scrollToTaskId = localStorage.getItem('scrollToTaskId');
    if (scrollToTaskId) {
      localStorage.removeItem('scrollToTaskId');
      // Wait for tasks to load, then scroll
      setTimeout(() => {
        const taskElement = document.querySelector(`[data-task-id="${scrollToTaskId}"]`);
        if (taskElement) {
          taskElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
          // Highlight the task briefly
          taskElement.style.backgroundColor = '#fef3c7';
          taskElement.style.borderColor = '#f59e0b';
          setTimeout(() => {
            taskElement.style.backgroundColor = '';
            taskElement.style.borderColor = '';
          }, 3000);
        }
      }, 1000);
    }
    
    // Check if we need to open create task form
    const openCreateTaskForm = localStorage.getItem('openCreateTaskForm');
    if (openCreateTaskForm) {
      localStorage.removeItem('openCreateTaskForm');
      setTimeout(() => {
        setShowTaskForm(true);
        setEditingTask(null);
      }, 500);
    }
  };

  // Handle real-time task updates
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'task_update') {
      handleRealTimeTaskUpdate(lastMessage);
    }
  }, [lastMessage]);

  const handleRealTimeTaskUpdate = (message) => {
    const { action, task } = message;

    switch (action) {
      case 'created':
        // Add new task to the list
        setTasks(prevTasks => {
          // Check if task already exists to avoid duplicates
          const exists = prevTasks.some(t => t.id === task.id);
          if (!exists) {
            return [task, ...prevTasks];
          }
          return prevTasks;
        });
        
        // Mark as recently updated
        setRecentlyUpdatedTasks(prev => new Set([...prev, task.id]));
        // Remove from recently updated after 5 seconds
        setTimeout(() => {
          setRecentlyUpdatedTasks(prev => {
            const newSet = new Set(prev);
            newSet.delete(task.id);
            return newSet;
          });
        }, 5000);
        break;

      case 'updated':
        // Update existing task
        setTasks(prevTasks => 
          prevTasks.map(t => 
            t.id === task.id ? { ...t, ...task } : t
          )
        );
        
        // Mark as recently updated
        setRecentlyUpdatedTasks(prev => new Set([...prev, task.id]));
        // Remove from recently updated after 5 seconds
        setTimeout(() => {
          setRecentlyUpdatedTasks(prev => {
            const newSet = new Set(prev);
            newSet.delete(task.id);
            return newSet;
          });
        }, 5000);
        break;

      case 'deleted':
        // Remove task from the list
        setTasks(prevTasks => 
          prevTasks.filter(t => t.id !== task.id)
        );
        break;

      default:
        console.log('Unknown task update action:', action);
    }
  };

  const fetchTasks = async () => {
    try {
      const response = await axios.get(`${API}/tasks`);
      setTasks(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching tasks:", error);
      setLoading(false);
    }
  };

  const fetchProjects = async () => {
    try {
      const response = await axios.get(`${API}/projects`);
      setProjects(response.data);
    } catch (error) {
      console.error("Error fetching projects:", error);
    }
  };

  const handleTaskSubmit = async (taskData) => {
    try {
      if (editingTask) {
        await axios.put(`${API}/tasks/${editingTask.id}`, taskData);
      } else {
        await axios.post(`${API}/tasks`, taskData);
      }
      
      await fetchTasks();
      setShowTaskForm(false);
      setEditingTask(null);
    } catch (error) {
      console.error("Error saving task:", error);
    }
  };

  const handleProjectSubmit = async (projectData) => {
    try {
      if (editingProject) {
        await axios.put(`${API}/projects/${editingProject.id}`, projectData);
      } else {
        await axios.post(`${API}/projects`, projectData);
      }
      
      await fetchProjects();
      setShowProjectForm(false);
      setEditingProject(null);
    } catch (error) {
      console.error("Error saving project:", error);
    }
  };

  const handleTaskDelete = async (taskId) => {
    if (window.confirm("Are you sure you want to delete this task?")) {
      try {
        await axios.delete(`${API}/tasks/${taskId}`);
        await fetchTasks();
      } catch (error) {
        console.error("Error deleting task:", error);
      }
    }
  };

  const handleTaskStatusChange = async (taskId, newStatus) => {
    try {
      await axios.put(`${API}/tasks/${taskId}`, { status: newStatus });
      await fetchTasks();
    } catch (error) {
      console.error("Error updating task status:", error);
    }
  };

  const handleTaskUpdate = async (updatedTask) => {
    // Update the local state immediately for real-time feedback
    setTasks(prevTasks => 
      prevTasks.map(task => 
        task.id === updatedTask.id ? updatedTask : task
      )
    );
    // Optionally refetch from server
    await fetchTasks();
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading tasks...</p>
      </div>
    );
  }

  return (
    <div className="task-manager">
      {/* Header */}
      <div className="manager-header">
        <h1 className="manager-title">Task Management</h1>
        <div className="header-actions">
          <button
            onClick={() => setShowTaskForm(true)}
            className="btn btn-primary"
          >
            <svg fill="currentColor" viewBox="0 0 24 24" className="btn-icon">
              <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
            </svg>
            New Task
          </button>
          <button
            onClick={() => setShowProjectForm(true)}
            className="btn btn-secondary"
          >
            <svg fill="currentColor" viewBox="0 0 24 24" className="btn-icon">
              <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
            </svg>
            New Project
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="tab-container">
        <div className="tab-list">
          {[
            { id: "tasks", label: "List View", icon: "📋" },
            { id: "kanban", label: "Kanban Board", icon: "📊" },
            { id: "projects", label: "Projects", icon: "📁" },
            { id: "calendar", label: "Calendar", icon: "📅" },
            { id: "gantt", label: "Gantt Chart", icon: "📈" }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`tab-button ${activeTab === tab.id ? 'tab-active' : ''}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Project Filter */}
        {(activeTab === "tasks" || activeTab === "kanban") && (
          <div className="filters">
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="filter-select"
            >
              <option value="">All Projects</option>
              {projects.map(project => (
                <option key={project.id} value={project.id}>{project.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="tab-content">
        {activeTab === "tasks" && (
          <div className="task-list">
            {tasks
              .filter(task => !selectedProject || task.project_id === selectedProject)
              .map(task => (
                <TaskCard
                  key={task.id}
                  task={task}
                  recentlyUpdated={recentlyUpdatedTasks.has(task.id)}
                  onEdit={(task) => {
                    setEditingTask(task);
                    setShowTaskForm(true);
                  }}
                  onDelete={handleTaskDelete}
                  onStatusChange={handleTaskStatusChange}
                  onTaskUpdate={handleTaskUpdate}
                />
              ))}
          </div>
        )}

        {activeTab === "kanban" && (
          <EnhancedKanbanBoard
            tasks={tasks}
            onTaskUpdate={handleTaskStatusChange}
            onTaskDelete={handleTaskDelete}
            onTaskEdit={(task) => {
              setEditingTask(task);
              setShowTaskForm(true);
            }}
            onTimerUpdate={handleTaskUpdate}
            projects={projects}
            selectedProject={selectedProject}
          />
        )}

        {activeTab === "projects" && (
          <div className="project-list">
            {projects.map(project => (
              <div key={project.id} className="project-card">
                <div className="project-header">
                  <div>
                    <h3 className="project-title">{project.name}</h3>
                    <p className="project-description">{project.description}</p>
                  </div>
                  <div className="project-actions">
                    <button 
                      onClick={() => {
                        setEditingProject(project);
                        setShowProjectForm(true);
                      }}
                      className="action-btn edit-btn"
                    >
                      <svg fill="currentColor" viewBox="0 0 24 24">
                        <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                      </svg>
                    </button>
                  </div>
                </div>
                <div className="project-stats">
                  <div className="stat">
                    <span className="stat-value">{project.task_count}</span>
                    <span className="stat-label">Tasks</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">{project.completed_task_count}</span>
                    <span className="stat-label">Completed</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">
                      {project.task_count > 0 
                        ? Math.round((project.completed_task_count / project.task_count) * 100) 
                        : 0}%
                    </span>
                    <span className="stat-label">Progress</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === "calendar" && (
          <CalendarView
            tasks={tasks}
            onTaskUpdate={(taskId, updates) => {
              handleTaskStatusChange(taskId, updates.status || tasks.find(t => t.id === taskId)?.status);
            }}
            onTaskCreate={handleTaskSubmit}
          />
        )}

        {activeTab === "gantt" && (
          <GanttChart
            tasks={tasks}
            projects={projects}
            onTaskUpdate={(taskId, updates) => {
              if (updates.status) {
                handleTaskStatusChange(taskId, updates.status);
              }
              // Handle other updates like time changes
            }}
          />
        )}
      </div>

      {/* Forms */}
      {showTaskForm && (
        <TaskForm
          task={editingTask}
          projects={projects}
          onSubmit={handleTaskSubmit}
          onCancel={() => {
            setShowTaskForm(false);
            setEditingTask(null);
          }}
        />
      )}

      {showProjectForm && (
        <ProjectForm
          project={editingProject}
          onSubmit={handleProjectSubmit}
          onCancel={() => {
            setShowProjectForm(false);
            setEditingProject(null);
          }}
        />
      )}
    </div>
  );
};

export default TaskManager;