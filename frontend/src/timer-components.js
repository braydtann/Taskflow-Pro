import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Timer Display Component
export const TimerDisplay = ({ seconds, isRunning, size = 'normal' }) => {
  const formatTime = (totalSeconds) => {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;
    
    if (hours > 0) {
      return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
      return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
  };

  const sizeClasses = {
    small: 'timer-display-small',
    normal: 'timer-display-normal',
    large: 'timer-display-large'
  };

  return (
    <div className={`timer-display ${sizeClasses[size]} ${isRunning ? 'timer-running' : 'timer-stopped'}`}>
      <svg className="timer-icon" fill="currentColor" viewBox="0 0 24 24">
        <path d="M15 1H9v2h6V1zm-4 13h2V8h-2v6zm8.03-6.61l1.42-1.42c-.43-.51-.9-.99-1.41-1.41l-1.42 1.42A8.962 8.962 0 0012 4c-4.97 0-9 4.03-9 9s4.02 9 9 9 9-4.03 9-9c0-2.11-.74-4.06-1.97-5.61zM12 20c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/>
      </svg>
      <span className="timer-time">{formatTime(seconds)}</span>
      {isRunning && <div className="timer-pulse"></div>}
    </div>
  );
};

// Timer Controls Component
export const TimerControls = ({ task, onTimerUpdate, compact = false }) => {
  const [timerStatus, setTimerStatus] = useState({
    is_timer_running: task?.is_timer_running || false,
    total_current_seconds: task?.timer_elapsed_seconds || 0,
    current_session_seconds: 0
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Real-time timer update
  useEffect(() => {
    let intervalId;
    
    if (timerStatus.is_timer_running) {
      intervalId = setInterval(() => {
        setTimerStatus(prev => ({
          ...prev,
          current_session_seconds: prev.current_session_seconds + 1,
          total_current_seconds: prev.total_current_seconds + 1
        }));
      }, 1000);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [timerStatus.is_timer_running]);

  // Fetch timer status
  const fetchTimerStatus = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/tasks/${task.id}/timer/status`);
      setTimerStatus(response.data);
    } catch (error) {
      console.error('Error fetching timer status:', error);
    }
  }, [task.id]);

  // Initialize timer status
  useEffect(() => {
    fetchTimerStatus();
  }, [fetchTimerStatus]);

  const handleStartTimer = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.post(`${API}/tasks/${task.id}/timer/start`);
      setTimerStatus({
        is_timer_running: true,
        total_current_seconds: task.timer_elapsed_seconds || 0,
        current_session_seconds: 0
      });
      if (onTimerUpdate) {
        onTimerUpdate(response.data.task);
      }
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to start timer');
    } finally {
      setLoading(false);
    }
  };

  const handlePauseTimer = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.post(`${API}/tasks/${task.id}/timer/pause`);
      setTimerStatus(prev => ({
        ...prev,
        is_timer_running: false,
        total_current_seconds: response.data.total_elapsed_seconds,
        current_session_seconds: 0
      }));
      if (onTimerUpdate) {
        onTimerUpdate(response.data.task);
      }
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to pause timer');
    } finally {
      setLoading(false);
    }
  };

  const handleResumeTimer = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.post(`${API}/tasks/${task.id}/timer/resume`);
      setTimerStatus(prev => ({
        ...prev,
        is_timer_running: true,
        current_session_seconds: 0
      }));
      if (onTimerUpdate) {
        onTimerUpdate(response.data.task);
      }
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to resume timer');
    } finally {
      setLoading(false);
    }
  };

  const handleStopTimer = async (completeTask = false) => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.post(`${API}/tasks/${task.id}/timer/stop?complete_task=${completeTask}`);
      setTimerStatus(prev => ({
        ...prev,
        is_timer_running: false,
        total_current_seconds: response.data.total_elapsed_seconds,
        current_session_seconds: 0
      }));
      if (onTimerUpdate) {
        onTimerUpdate(response.data.task);
      }
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to stop timer');
    } finally {
      setLoading(false);
    }
  };

  const hasElapsedTime = timerStatus.total_current_seconds > 0;
  const isRunning = timerStatus.is_timer_running;

  if (compact) {
    return (
      <div className="timer-controls-compact">
        {error && <div className="timer-error">{error}</div>}
        
        <div className="timer-section">
          <TimerDisplay 
            seconds={timerStatus.total_current_seconds} 
            isRunning={isRunning}
            size="small"
          />
          
          <div className="timer-buttons-compact">
            {!isRunning && !hasElapsedTime && (
              <button
                onClick={handleStartTimer}
                disabled={loading}
                className="timer-btn timer-btn-start"
                title="Start Timer"
              >
                <svg fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z"/>
                </svg>
              </button>
            )}
            
            {isRunning && (
              <button
                onClick={handlePauseTimer}
                disabled={loading}
                className="timer-btn timer-btn-pause"
                title="Pause Timer"
              >
                <svg fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                </svg>
              </button>
            )}
            
            {!isRunning && hasElapsedTime && (
              <button
                onClick={handleResumeTimer}
                disabled={loading}
                className="timer-btn timer-btn-resume"
                title="Resume Timer"
              >
                <svg fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z"/>
                </svg>
              </button>
            )}
            
            {hasElapsedTime && (
              <button
                onClick={() => handleStopTimer(false)}
                disabled={loading}
                className="timer-btn timer-btn-stop"
                title="Stop Timer"
              >
                <svg fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 6h12v12H6z"/>
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="timer-controls">
      {error && <div className="timer-error">{error}</div>}
      
      <div className="timer-section">
        <TimerDisplay 
          seconds={timerStatus.total_current_seconds} 
          isRunning={isRunning}
        />
        
        <div className="timer-buttons">
          {!isRunning && !hasElapsedTime && (
            <button
              onClick={handleStartTimer}
              disabled={loading}
              className="timer-btn timer-btn-start"
            >
              <svg fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z"/>
              </svg>
              Start Timer
            </button>
          )}
          
          {isRunning && (
            <button
              onClick={handlePauseTimer}
              disabled={loading}
              className="timer-btn timer-btn-pause"
            >
              <svg fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
              </svg>
              Pause Timer
            </button>
          )}
          
          {!isRunning && hasElapsedTime && (
            <>
              <button
                onClick={handleResumeTimer}
                disabled={loading}
                className="timer-btn timer-btn-resume"
              >
                <svg fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z"/>
                </svg>
                Resume
              </button>
              
              <button
                onClick={() => handleStopTimer(false)}
                disabled={loading}
                className="timer-btn timer-btn-stop"
              >
                <svg fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 6h12v12H6z"/>
                </svg>
                Stop
              </button>
              
              <button
                onClick={() => handleStopTimer(true)}
                disabled={loading}
                className="timer-btn timer-btn-complete"
              >
                <svg fill="currentColor" viewBox="0 0 24 24">
                  <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
                Complete Task
              </button>
            </>
          )}
        </div>
      </div>
      
      {hasElapsedTime && (
        <div className="timer-stats">
          <div className="timer-stat">
            <span className="stat-label">Total Time:</span>
            <span className="stat-value">{Math.round(timerStatus.total_current_seconds / 60)} min</span>
          </div>
          {task.estimated_duration && (
            <div className="timer-stat">
              <span className="stat-label">Estimated:</span>
              <span className="stat-value">{task.estimated_duration} min</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Timer Summary Component for displaying elapsed time
export const TimerSummary = ({ task }) => {
  const totalMinutes = Math.round((task.timer_elapsed_seconds || 0) / 60);
  const isRunning = task.is_timer_running;
  
  if (totalMinutes === 0 && !isRunning) {
    return null;
  }

  return (
    <div className="timer-summary">
      <TimerDisplay 
        seconds={task.timer_elapsed_seconds || 0} 
        isRunning={isRunning}
        size="small"
      />
      {task.estimated_duration && totalMinutes > 0 && (
        <div className="timer-progress">
          <div className="progress-bar">
            <div 
              className="progress-fill"
              style={{ 
                width: `${Math.min((totalMinutes / task.estimated_duration) * 100, 100)}%`,
                backgroundColor: totalMinutes > task.estimated_duration ? '#ef4444' : '#10b981'
              }}
            ></div>
          </div>
          <span className="progress-text">
            {totalMinutes}/{task.estimated_duration}min
          </span>
        </div>
      )}
    </div>
  );
};