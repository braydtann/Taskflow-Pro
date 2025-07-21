import React, { useState, useCallback } from 'react';
import { Calendar, momentLocalizer } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { Gantt, Task, EventOption, StylingOption, ViewMode, DisplayOption } from 'gantt-task-react';
import "gantt-task-react/dist/index.css";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import {
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { TimerControls } from './timer-components';

const localizer = momentLocalizer(moment);

// Calendar View Component
export const CalendarView = ({ tasks, onTaskUpdate, onTaskCreate }) => {
  const [view, setView] = useState('month');
  
  // Convert tasks to calendar events
  const events = tasks.map(task => {
    const startDate = task.start_time 
      ? new Date(task.start_time)
      : task.due_date 
        ? new Date(task.due_date)
        : new Date();
    
    const endDate = task.end_time 
      ? new Date(task.end_time)
      : task.estimated_duration
        ? new Date(startDate.getTime() + task.estimated_duration * 60000)
        : new Date(startDate.getTime() + 60 * 60000); // 1 hour default
    
    return {
      id: task.id,
      title: task.title,
      start: startDate,
      end: endDate,
      resource: {
        task,
        priority: task.priority,
        status: task.status,
        project: task.project_name
      }
    };
  });

  // Event styling based on priority and status
  const eventStyleGetter = (event, start, end, isSelected) => {
    const { priority, status } = event.resource;
    
    let backgroundColor = '#7c3aed'; // default purple
    
    if (status === 'completed') {
      backgroundColor = '#10b981';
    } else if (priority === 'urgent') {
      backgroundColor = '#ef4444';
    } else if (priority === 'high') {
      backgroundColor = '#f59e0b';
    } else if (priority === 'low') {
      backgroundColor = '#6b7280';
    }

    return {
      style: {
        backgroundColor,
        borderRadius: '8px',
        opacity: status === 'completed' ? 0.7 : 0.9,
        color: 'white',
        border: '0px',
        display: 'block',
        fontSize: '12px',
        fontWeight: '500'
      }
    };
  };

  // Handle event selection
  const onSelectEvent = (event) => {
    // Open task details or edit form
    console.log('Selected event:', event);
  };

  // Handle slot selection for creating new tasks
  const onSelectSlot = ({ start, end }) => {
    const title = window.prompt('New task title:');
    if (title) {
      const newTask = {
        title,
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        estimated_duration: Math.round((end - start) / 60000), // in minutes
        priority: 'medium',
        status: 'todo'
      };
      onTaskCreate(newTask);
    }
  };

  // Handle event drag and drop
  const onEventDrop = ({ event, start, end }) => {
    const updatedTask = {
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      estimated_duration: Math.round((end - start) / 60000)
    };
    onTaskUpdate(event.id, updatedTask);
  };

  return (
    <div className="calendar-container">
      <div className="calendar-header">
        <h3 className="calendar-title">Task Calendar</h3>
        <div className="calendar-controls">
          <div className="view-switcher">
            {['month', 'week', 'day', 'agenda'].map(viewName => (
              <button
                key={viewName}
                onClick={() => setView(viewName)}
                className={`view-btn ${view === viewName ? 'active' : ''}`}
              >
                {viewName.charAt(0).toUpperCase() + viewName.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>
      
      <div className="calendar-legend">
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#ef4444' }}></div>
          <span>Urgent</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#f59e0b' }}></div>
          <span>High Priority</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#7c3aed' }}></div>
          <span>Medium Priority</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#10b981' }}></div>
          <span>Completed</span>
        </div>
      </div>

      <div className="calendar-wrapper">
        <Calendar
          localizer={localizer}
          events={events}
          startAccessor="start"
          endAccessor="end"
          style={{ height: 600 }}
          view={view}
          onView={setView}
          eventPropGetter={eventStyleGetter}
          onSelectEvent={onSelectEvent}
          onSelectSlot={onSelectSlot}
          onEventDrop={onEventDrop}
          selectable
          resizable
          popup
          showMultiDayTimes
        />
      </div>
    </div>
  );
};

// Gantt Chart Component
export const GanttChart = ({ tasks, projects, onTaskUpdate }) => {
  const [viewMode, setViewMode] = useState(ViewMode.Week);
  
  // Convert tasks to Gantt format
  const ganttTasks = tasks.map(task => {
    const startDate = task.start_time 
      ? new Date(task.start_time)
      : task.created_at
        ? new Date(task.created_at)
        : new Date();
    
    const duration = task.estimated_duration || 60; // default 1 hour
    const endDate = task.end_time
      ? new Date(task.end_time) 
      : new Date(startDate.getTime() + duration * 60000);

    return {
      start: startDate,
      end: endDate,
      name: task.title,
      id: task.id,
      type: task.status === 'completed' ? 'task' : 'task',
      progress: task.status === 'completed' ? 100 : task.status === 'in_progress' ? 50 : 0,
      isDisabled: false,
      styles: {
        progressColor: task.status === 'completed' ? '#10b981' : '#7c3aed',
        progressSelectedColor: task.status === 'completed' ? '#059669' : '#6d28d9',
        backgroundColor: getGanttTaskColor(task.priority),
        backgroundSelectedColor: getGanttTaskSelectedColor(task.priority)
      },
      project: task.project_name || 'No Project'
    };
  });

  // Group tasks by project for better visualization
  const ganttTasksWithProjects = [];
  const projectGroups = {};

  // First add project headers
  projects.forEach(project => {
    projectGroups[project.id] = {
      start: new Date(),
      end: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days from now
      name: project.name,
      id: `project-${project.id}`,
      type: 'project',
      progress: project.task_count > 0 ? (project.completed_task_count / project.task_count) * 100 : 0,
      hideChildren: false,
      styles: {
        progressColor: '#7c3aed',
        progressSelectedColor: '#6d28d9',
        backgroundColor: '#e2e8f0',
        backgroundSelectedColor: '#cbd5e1'
      }
    };
    ganttTasksWithProjects.push(projectGroups[project.id]);
  });

  // Add tasks under their projects
  ganttTasks.forEach(task => {
    const projectTask = tasks.find(t => t.id === task.id);
    if (projectTask && projectTask.project_id) {
      // Add project prefix to show hierarchy
      task.id = `${projectTask.project_id}-${task.id}`;
    }
    ganttTasksWithProjects.push(task);
  });

  function getGanttTaskColor(priority) {
    switch (priority) {
      case 'urgent': return '#fecaca';
      case 'high': return '#fed7aa';
      case 'medium': return '#e0e7ff';
      case 'low': return '#f3f4f6';
      default: return '#e0e7ff';
    }
  }

  function getGanttTaskSelectedColor(priority) {
    switch (priority) {
      case 'urgent': return '#f87171';
      case 'high': return '#fb923c';
      case 'medium': return '#a5b4fc';
      case 'low': return '#d1d5db';
      default: return '#a5b4fc';
    }
  }

  const handleTaskChange = (task) => {
    const originalTaskId = task.id.includes('-') ? task.id.split('-')[1] : task.id;
    const updatedTask = {
      start_time: task.start.toISOString(),
      end_time: task.end.toISOString(),
      estimated_duration: Math.round((task.end - task.start) / 60000)
    };
    onTaskUpdate(originalTaskId, updatedTask);
  };

  const handleProgressChange = (task) => {
    const originalTaskId = task.id.includes('-') ? task.id.split('-')[1] : task.id;
    let status = 'todo';
    if (task.progress >= 100) status = 'completed';
    else if (task.progress > 0) status = 'in_progress';
    
    onTaskUpdate(originalTaskId, { status });
  };

  return (
    <div className="gantt-container">
      <div className="gantt-header">
        <h3 className="gantt-title">Project Timeline</h3>
        <div className="gantt-controls">
          <div className="view-switcher">
            {[
              { mode: ViewMode.Hour, label: 'Hour' },
              { mode: ViewMode.QuarterDay, label: '6 Hours' },
              { mode: ViewMode.HalfDay, label: '12 Hours' },
              { mode: ViewMode.Day, label: 'Day' },
              { mode: ViewMode.Week, label: 'Week' },
              { mode: ViewMode.Month, label: 'Month' }
            ].map(({ mode, label }) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`view-btn ${viewMode === mode ? 'active' : ''}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="gantt-wrapper">
        <Gantt
          tasks={ganttTasksWithProjects}
          viewMode={viewMode}
          onDateChange={handleTaskChange}
          onProgressChange={handleProgressChange}
          onDoubleClick={(task) => console.log('Double clicked:', task)}
          columnWidth={viewMode === ViewMode.Month ? 300 : 100}
          listCellWidth="200px"
          rowHeight={50}
          barCornerRadius={8}
          handleWidth={8}
          fontFamily="inherit"
          fontSize="14px"
          barFill={60}
          barProgressColor="#7c3aed"
          barProgressSelectedColor="#6d28d9"
          barBackgroundColor="#e0e7ff"
          barBackgroundSelectedColor="#c7d2fe"
          projectProgressColor="#7c3aed"
          projectProgressSelectedColor="#6d28d9"
          projectBackgroundColor="#f1f5f9"
          projectBackgroundSelectedColor="#e2e8f0"
          milestoneBackgroundColor="#f59e0b"
          milestoneBackgroundSelectedColor="#d97706"
          rtl={false}
        />
      </div>
    </div>
  );
};

// Enhanced Draggable Kanban Card
const DraggableKanbanCard = ({ task, onEdit, onDelete, onStatusChange, onTaskUpdate }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: task.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const priorityColors = {
    low: "bg-green-100 text-green-800",
    medium: "bg-yellow-100 text-yellow-800",
    high: "bg-orange-100 text-orange-800",
    urgent: "bg-red-100 text-red-800"
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`kanban-card draggable ${task.is_timer_running ? 'kanban-card-timer-active' : ''}`}
      data-task-id={task.id}
    >
      <div className="kanban-card-header">
        <h4 className="kanban-card-title">{task.title}</h4>
        <div className="kanban-card-actions">
          <button onClick={() => onEdit(task)} className="action-btn edit-btn-small">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z"/>
            </svg>
          </button>
          <button onClick={() => onDelete(task.id)} className="action-btn delete-btn-small">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12z"/>
            </svg>
          </button>
        </div>
      </div>
      
      {task.description && (
        <p className="kanban-card-description">{task.description}</p>
      )}

      {/* Timer Section for Kanban */}
      <div className="kanban-timer-section">
        <TimerControls 
          task={task} 
          onTimerUpdate={onTaskUpdate}
          compact={true}
        />
      </div>

      <div className="kanban-card-meta">
        <span className={`priority-badge ${priorityColors[task.priority]}`}>
          {task.priority}
        </span>
        {task.estimated_duration && (
          <span className="duration-badge">
            Est: {Math.round(task.estimated_duration / 60)}h
          </span>
        )}
        {(task.timer_elapsed_seconds > 0 || task.is_timer_running) && (
          <span className="actual-duration-badge">
            Actual: {Math.round((task.timer_elapsed_seconds || 0) / 60)} min
          </span>
        )}
      </div>

      {task.assigned_users && task.assigned_users.length > 0 && (
        <div className="kanban-card-owners">
          <div className="owner-avatars">
            {task.assigned_users.slice(0, 3).map((owner, index) => (
              <div key={index} className="owner-avatar">
                {owner.charAt(0).toUpperCase()}
              </div>
            ))}
            {task.assigned_users.length > 3 && (
              <div className="owner-avatar more">+{task.assigned_users.length - 3}</div>
            )}
          </div>
        </div>
      )}

      {task.due_date && (
        <div className="kanban-card-due">
          <svg fill="currentColor" viewBox="0 0 24 24" className="due-icon">
            <path d="M9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm2-7h-1V2h-2v2H8V2H6v2H5c-1.1 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z"/>
          </svg>
          <span>{new Date(task.due_date).toLocaleDateString()}</span>
        </div>
      )}
    </div>
  );
};

// Droppable Column Component for Kanban
const DroppableColumn = ({ column, children }) => {
  const { isOver, setNodeRef } = useDroppable({
    id: column.id,
  });

  const style = {
    backgroundColor: isOver ? '#e0f2fe' : column.color,
    transition: 'background-color 0.2s',
  };

  return (
    <div 
      ref={setNodeRef}
      className="kanban-column enhanced" 
      style={style}
    >
      {children}
    </div>
  );
};

// Enhanced Kanban Board with Drag and Drop
export const EnhancedKanbanBoard = ({ tasks, onTaskUpdate, onTaskDelete, projects, selectedProject, onTaskEdit, onTimerUpdate }) => {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const filteredTasks = selectedProject 
    ? tasks.filter(task => task.project_id === selectedProject)
    : tasks;

  const columns = [
    { id: "todo", title: "To Do 📝", status: "todo", color: "#f1f5f9" },
    { id: "in_progress", title: "In Progress ⚡", status: "in_progress", color: "#eff6ff" },
    { id: "completed", title: "Completed ✅", status: "completed", color: "#f0fdf4" }
  ];

  function handleDragEnd(event) {
    const { active, over } = event;
    
    console.log('Drag end event:', { active: active?.id, over: over?.id });

    if (!over) {
      console.log('No drop target found');
      return;
    }

    const activeTask = filteredTasks.find(task => task.id === active.id);
    if (!activeTask) {
      console.log('Active task not found:', active.id);
      return;
    }

    // Determine new status from drop zone
    let newStatus = activeTask.status;
    
    // Check if dropped on a column (droppable zone)
    const targetColumn = columns.find(col => col.id === over.id);
    if (targetColumn) {
      newStatus = over.id;
      console.log('Dropped on column:', targetColumn.title);
    } else {
      // Dropped on another task, find the column that task belongs to
      const overTask = filteredTasks.find(task => task.id === over.id);
      if (overTask) {
        newStatus = overTask.status;
        console.log('Dropped on task:', overTask.title, 'in column:', newStatus);
      } else {
        console.log('Unknown drop target:', over.id);
      }
    }

    // Only update if status actually changed
    if (newStatus !== activeTask.status) {
      console.log(`Moving task "${activeTask.title}" from ${activeTask.status} to ${newStatus}`);
      onTaskUpdate(active.id, newStatus);
    } else {
      console.log('Task status unchanged:', newStatus);
    }
  }

  const handleTaskUpdate = async (updatedTask) => {
    if (onTimerUpdate) {
      onTimerUpdate(updatedTask);
    }
  };

  return (
    <div className="enhanced-kanban-board">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        {columns.map(column => {
          const columnTasks = filteredTasks.filter(task => task.status === column.status);
          
          return (
            <DroppableColumn key={column.id} column={column}>
              <div className="kanban-header enhanced">
                <h3 className="kanban-title">{column.title}</h3>
                <div className="kanban-stats">
                  <span className="task-count">{columnTasks.length}</span>
                  {columnTasks.length > 0 && (
                    <>
                      <span className="estimated-time">
                        {Math.round(columnTasks.reduce((sum, task) => sum + (task.estimated_duration || 0), 0) / 60)}h est
                      </span>
                      <span className="actual-time">
                        {Math.round(columnTasks.reduce((sum, task) => sum + (task.timer_elapsed_seconds || 0), 0) / 3600)}h actual
                      </span>
                    </>
                  )}
                </div>
              </div>
              
              <div className="kanban-tasks enhanced" id={column.id}>
                <SortableContext items={columnTasks.map(task => task.id)} strategy={verticalListSortingStrategy}>
                  {columnTasks.map(task => (
                    <DraggableKanbanCard
                      key={task.id}
                      task={task}
                      onEdit={onTaskEdit}
                      onDelete={onTaskDelete}
                      onStatusChange={onTaskUpdate}
                      onTaskUpdate={handleTaskUpdate}
                    />
                  ))}
                </SortableContext>
              </div>
              
              {columnTasks.length === 0 && (
                <div className="empty-column">
                  <p>Drop tasks here</p>
                </div>
              )}
            </DroppableColumn>
          );
        })}
      </DndContext>
    </div>
  );
};

// Smart Scheduling Recommendations Component
export const SmartScheduling = ({ task, existingTasks, onScheduleRecommendation }) => {
  const [recommendations, setRecommendations] = useState([]);

  // Generate scheduling recommendations based on task duration and existing schedule
  const generateRecommendations = useCallback(() => {
    if (!task.estimated_duration) return [];

    const duration = task.estimated_duration * 60000; // convert to milliseconds
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const recs = [];

    // Get busy times from existing tasks
    const busyTimes = existingTasks
      .filter(t => t.start_time && t.end_time)
      .map(t => ({
        start: new Date(t.start_time),
        end: new Date(t.end_time)
      }));

    // Generate recommendations for next 7 days
    for (let day = 0; day < 7; day++) {
      const currentDay = new Date(today);
      currentDay.setDate(today.getDate() + day);
      
      // Working hours: 9 AM to 6 PM
      const workStart = new Date(currentDay);
      workStart.setHours(9, 0, 0, 0);
      const workEnd = new Date(currentDay);
      workEnd.setHours(18, 0, 0, 0);

      // Find available slots
      let currentTime = new Date(workStart);
      while (currentTime < workEnd) {
        const slotEnd = new Date(currentTime.getTime() + duration);
        
        if (slotEnd <= workEnd) {
          // Check if this slot conflicts with existing tasks
          const hasConflict = busyTimes.some(busy => 
            (currentTime >= busy.start && currentTime < busy.end) ||
            (slotEnd > busy.start && slotEnd <= busy.end) ||
            (currentTime <= busy.start && slotEnd >= busy.end)
          );

          if (!hasConflict) {
            const score = calculateScore(currentTime, day, task.priority);
            recs.push({
              start: new Date(currentTime),
              end: new Date(slotEnd),
              score,
              reason: getReasonText(currentTime, day, score)
            });
          }
        }
        
        currentTime.setMinutes(currentTime.getMinutes() + 30); // 30-minute intervals
      }
    }

    // Sort by score and take top 5
    return recs.sort((a, b) => b.score - a.score).slice(0, 5);
  }, [task, existingTasks]);

  function calculateScore(time, day, priority) {
    let score = 100;
    
    // Prefer mornings for high priority tasks
    if (priority === 'high' || priority === 'urgent') {
      if (time.getHours() < 12) score += 20;
    }
    
    // Penalize later in the week
    score -= day * 5;
    
    // Prefer earlier in the day for better productivity
    if (time.getHours() >= 9 && time.getHours() <= 11) score += 15;
    
    // Slight penalty for very early or late hours
    if (time.getHours() < 9 || time.getHours() > 16) score -= 10;
    
    return score;
  }

  function getReasonText(time, day, score) {
    if (score > 110) return "Optimal time - high productivity period";
    if (score > 100) return "Good time - fits well with schedule";
    if (day === 0) return "Today - immediate availability";
    if (time.getHours() < 12) return "Morning slot - better focus";
    return "Available slot - consider your energy levels";
  }

  React.useEffect(() => {
    setRecommendations(generateRecommendations());
  }, [generateRecommendations]);

  if (!task.estimated_duration || recommendations.length === 0) {
    return null;
  }

  return (
    <div className="smart-scheduling">
      <h4 className="scheduling-title">🤖 Smart Scheduling Recommendations</h4>
      <p className="scheduling-subtitle">
        Based on your task duration ({Math.round(task.estimated_duration / 60)}h) and current schedule
      </p>
      
      <div className="recommendations-list">
        {recommendations.map((rec, index) => (
          <div key={index} className="recommendation-item">
            <div className="rec-time">
              <div className="rec-date">
                {rec.start.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
              </div>
              <div className="rec-hours">
                {rec.start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })} - 
                {rec.end.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
              </div>
            </div>
            
            <div className="rec-details">
              <div className="rec-score">
                <div className="score-bar">
                  <div 
                    className="score-fill" 
                    style={{ width: `${Math.min(rec.score, 120)}%` }}
                  ></div>
                </div>
                <span className="score-text">{rec.score}% match</span>
              </div>
              <div className="rec-reason">{rec.reason}</div>
            </div>
            
            <button 
              className="schedule-btn"
              onClick={() => onScheduleRecommendation({
                ...task,
                start_time: rec.start.toISOString(),
                end_time: rec.end.toISOString()
              })}
            >
              Schedule
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};