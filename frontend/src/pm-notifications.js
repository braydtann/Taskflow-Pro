import React, { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from './auth';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Notifications Component
export const PMNotifications = () => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, unread
  const { user } = useAuth();

  useEffect(() => {
    fetchNotifications();
    // Set up polling for new notifications
    const interval = setInterval(fetchNotifications, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, [filter]);

  const fetchNotifications = async () => {
    try {
      const unreadOnly = filter === 'unread';
      const response = await axios.get(`${API}/pm/notifications?unread_only=${unreadOnly}`);
      setNotifications(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching notifications:", error);
      setLoading(false);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      await axios.put(`${API}/pm/notifications/${notificationId}/read`);
      // Update the notification in state
      setNotifications(prev => 
        prev.map(notif => 
          notif.id === notificationId 
            ? { ...notif, read: true }
            : notif
        )
      );
    } catch (error) {
      console.error("Error marking notification as read:", error);
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'overdue': return '⏰';
      case 'deadline': return '📅';
      case 'blocked': return '🚫';
      case 'project_update': return '📁';
      case 'task_status_alert': return '⚠️';
      case 'assignment': return '👤';
      default: return '📢';
    }
  };

  const getNotificationColor = (priority) => {
    switch (priority) {
      case 'high': return '#ef4444';
      case 'medium': return '#f59e0b';
      case 'low': return '#3b82f6';
      default: return '#6b7280';
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (minutes < 60) {
      return `${minutes}m ago`;
    } else if (hours < 24) {
      return `${hours}h ago`;
    } else if (days < 7) {
      return `${days}d ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  if (loading) {
    return (
      <div className="pm-notifications-container">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading notifications...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="pm-notifications-container">
      <div className="pm-notifications-header">
        <div className="pm-notifications-title">
          <h3>Notifications</h3>
          {unreadCount > 0 && (
            <span className="pm-notification-badge">{unreadCount}</span>
          )}
        </div>
        
        <div className="pm-notifications-controls">
          <div className="pm-filter-group">
            <button 
              className={`pm-filter-btn ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All
            </button>
            <button 
              className={`pm-filter-btn ${filter === 'unread' ? 'active' : ''}`}
              onClick={() => setFilter('unread')}
            >
              Unread ({unreadCount})
            </button>
          </div>
          
          <button className="pm-refresh-btn" onClick={fetchNotifications}>
            🔄 Refresh
          </button>
        </div>
      </div>

      <div className="pm-notifications-list">
        {notifications.map(notification => (
          <div 
            key={notification.id} 
            className={`pm-notification-item ${!notification.read ? 'unread' : ''}`}
            onClick={() => !notification.read && markAsRead(notification.id)}
          >
            <div className="pm-notification-icon">
              <span 
                className="pm-notification-icon-bg"
                style={{ backgroundColor: getNotificationColor(notification.priority) }}
              >
                {getNotificationIcon(notification.type)}
              </span>
            </div>
            
            <div className="pm-notification-content">
              <div className="pm-notification-header">
                <h4 className="pm-notification-title">{notification.title}</h4>
                <span className="pm-notification-time">
                  {formatTimestamp(notification.created_at)}
                </span>
              </div>
              
              <p className="pm-notification-message">{notification.message}</p>
              
              <div className="pm-notification-meta">
                <span className={`pm-notification-priority ${notification.priority}`}>
                  {notification.priority} priority
                </span>
                {notification.entity_type && (
                  <span className="pm-notification-entity">
                    {notification.entity_type}
                  </span>
                )}
              </div>
            </div>
            
            {!notification.read && (
              <div className="pm-notification-status">
                <div className="pm-notification-unread-dot"></div>
              </div>
            )}
          </div>
        ))}
      </div>

      {notifications.length === 0 && (
        <div className="pm-empty-state">
          <div className="pm-empty-icon">🔔</div>
          <h3>No Notifications</h3>
          <p>
            {filter === 'unread' 
              ? "You're all caught up! No unread notifications."
              : "No notifications to display at this time."
            }
          </p>
        </div>
      )}
    </div>
  );
};

// Notification Bell Component (for header)
export const PMNotificationBell = () => {
  const [unreadCount, setUnreadCount] = useState(0);
  const [showDropdown, setShowDropdown] = useState(false);
  const [recentNotifications, setRecentNotifications] = useState([]);

  useEffect(() => {
    fetchUnreadNotifications();
    const interval = setInterval(fetchUnreadNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchUnreadNotifications = async () => {
    try {
      const response = await axios.get(`${API}/pm/notifications?unread_only=true`);
      const unread = response.data;
      setUnreadCount(unread.length);
      setRecentNotifications(unread.slice(0, 5)); // Show only recent 5
    } catch (error) {
      console.error("Error fetching unread notifications:", error);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      await axios.put(`${API}/pm/notifications/${notificationId}/read`);
      await fetchUnreadNotifications();
    } catch (error) {
      console.error("Error marking notification as read:", error);
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'overdue': return '⏰';
      case 'deadline': return '📅';
      case 'blocked': return '🚫';
      case 'project_update': return '📁';
      case 'task_status_alert': return '⚠️';
      case 'assignment': return '👤';
      default: return '📢';
    }
  };

  return (
    <div className="pm-notification-bell">
      <button 
        className="pm-bell-button"
        onClick={() => setShowDropdown(!showDropdown)}
      >
        🔔
        {unreadCount > 0 && (
          <span className="pm-bell-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
        )}
      </button>

      {showDropdown && (
        <div className="pm-notification-dropdown">
          <div className="pm-dropdown-header">
            <h4>Recent Notifications</h4>
            <button 
              className="pm-dropdown-close"
              onClick={() => setShowDropdown(false)}
            >
              ✕
            </button>
          </div>

          <div className="pm-dropdown-content">
            {recentNotifications.length > 0 ? (
              <>
                {recentNotifications.map(notification => (
                  <div 
                    key={notification.id}
                    className="pm-dropdown-notification"
                    onClick={() => markAsRead(notification.id)}
                  >
                    <div className="pm-dropdown-icon">
                      {getNotificationIcon(notification.type)}
                    </div>
                    <div className="pm-dropdown-text">
                      <div className="pm-dropdown-title">{notification.title}</div>
                      <div className="pm-dropdown-message">{notification.message}</div>
                    </div>
                  </div>
                ))}
                
                <div className="pm-dropdown-footer">
                  <a href="/pm-notifications" className="pm-view-all-link">
                    View All Notifications
                  </a>
                </div>
              </>
            ) : (
              <div className="pm-dropdown-empty">
                <div className="pm-empty-icon">🔔</div>
                <p>No new notifications</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default PMNotifications;