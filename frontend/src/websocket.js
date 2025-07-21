import React, { createContext, useContext, useEffect, useState } from 'react';
import useWebSocket from 'use-websocket';
import { useAuth } from './auth';

const WebSocketContext = createContext();

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};

export const WebSocketProvider = ({ children }) => {
  const { user, token } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [taskUpdates, setTaskUpdates] = useState([]);
  const [onlineUsers, setOnlineUsers] = useState(new Set());

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
  const wsUrl = user ? `${BACKEND_URL.replace('http', 'ws')}/ws/${user.id}?token=${token}` : null;

  const {
    sendMessage,
    lastMessage: rawLastMessage,
    readyState
  } = useWebSocket(wsUrl, {
    shouldReconnect: () => true,
    reconnectAttempts: 5,
    reconnectInterval: 3000,
    onOpen: () => {
      console.log('🔗 WebSocket connected');
      setIsConnected(true);
    },
    onClose: () => {
      console.log('🔌 WebSocket disconnected');
      setIsConnected(false);
    },
    onError: (error) => {
      console.error('❌ WebSocket error:', error);
      setIsConnected(false);
    }
  }, user && token);

  // Process incoming messages
  useEffect(() => {
    if (rawLastMessage?.data) {
      try {
        const message = JSON.parse(rawLastMessage.data);
        setLastMessage(message);

        switch (message.type) {
          case 'task_update':
            setTaskUpdates(prev => [message, ...prev.slice(0, 49)]); // Keep last 50 updates
            
            // Show browser notification for task updates from other users
            if (message.user_id !== user?.id && message.action !== 'user_typing') {
              showNotification(message);
            }
            break;
            
          case 'user_online':
            setOnlineUsers(prev => new Set([...prev, message.user_id]));
            break;
            
          case 'user_offline':
            setOnlineUsers(prev => {
              const newSet = new Set(prev);
              newSet.delete(message.user_id);
              return newSet;
            });
            break;
            
          case 'connection_established':
            console.log('✅ Real-time updates enabled');
            break;
            
          default:
            console.log('📨 WebSocket message:', message);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    }
  }, [rawLastMessage, user?.id]);

  const showNotification = (message) => {
    if ('Notification' in window && Notification.permission === 'granted') {
      const title = getNotificationTitle(message);
      const body = getNotificationBody(message);
      
      new Notification(title, {
        body,
        icon: '/favicon.ico',
        tag: `task-${message.task.id}`,
        requireInteraction: false
      });
    }
  };

  const getNotificationTitle = (message) => {
    switch (message.action) {
      case 'created':
        return '🆕 New Task Created';
      case 'updated':
        return '📝 Task Updated';
      case 'deleted':
        return '🗑️ Task Deleted';
      default:
        return 'Task Update';
    }
  };

  const getNotificationBody = (message) => {
    const taskTitle = message.task.title || 'Untitled Task';
    switch (message.action) {
      case 'created':
        return `New task "${taskTitle}" was created`;
      case 'updated':
        return `Task "${taskTitle}" was updated`;
      case 'deleted':
        return `Task "${taskTitle}" was deleted`;
      default:
        return `Task "${taskTitle}" was modified`;
    }
  };

  // Request notification permission on first load
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          console.log('✅ Browser notifications enabled');
        }
      });
    }
  }, []);

  // Utility functions for sending messages
  const sendPing = () => {
    if (sendMessage && isConnected) {
      sendMessage(JSON.stringify({ type: 'ping' }));
    }
  };

  const sendTypingIndicator = (taskId) => {
    if (sendMessage && isConnected && taskId) {
      sendMessage(JSON.stringify({ 
        type: 'user_typing', 
        task_id: taskId,
        user_id: user?.id 
      }));
    }
  };

  const clearTaskUpdates = () => {
    setTaskUpdates([]);
  };

  const getRecentTaskUpdates = (limit = 10) => {
    return taskUpdates.slice(0, limit);
  };

  const value = {
    isConnected,
    lastMessage,
    taskUpdates,
    onlineUsers,
    sendPing,
    sendTypingIndicator,
    clearTaskUpdates,
    getRecentTaskUpdates,
    connectionState: readyState
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

// Connection state constants
export const ConnectionState = {
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3
};

// Real-time task updates hook
export const useTaskUpdates = () => {
  const { taskUpdates, clearTaskUpdates, getRecentTaskUpdates } = useWebSocketContext();
  
  return {
    taskUpdates,
    clearTaskUpdates,
    getRecentTaskUpdates,
    hasUpdates: taskUpdates.length > 0
  };
};

// Online users hook
export const useOnlineUsers = () => {
  const { onlineUsers } = useWebSocketContext();
  
  return {
    onlineUsers: Array.from(onlineUsers),
    isUserOnline: (userId) => onlineUsers.has(userId)
  };
};

export default WebSocketContext;