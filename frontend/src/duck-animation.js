import React, { useState, useEffect, useRef } from 'react';

// Duck Animation Component
const DuckAnimation = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState({ x: 100, y: window.innerHeight - 100 });
  const [isRunning, setIsRunning] = useState(false);
  const [direction, setDirection] = useState('right');
  const [lastActivity, setLastActivity] = useState(Date.now());
  const duckRef = useRef(null);
  const animationRef = useRef(null);
  const inactivityTimerRef = useRef(null);

  // Activity tracking
  useEffect(() => {
    const updateActivity = () => {
      setLastActivity(Date.now());
      if (isVisible) {
        setIsVisible(false);
      }
    };

    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
    
    events.forEach(event => {
      document.addEventListener(event, updateActivity, true);
    });

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, updateActivity, true);
      });
    };
  }, [isVisible]);

  // Inactivity timer (5 minutes = 300000ms)
  useEffect(() => {
    const checkInactivity = () => {
      const timeSinceLastActivity = Date.now() - lastActivity;
      if (timeSinceLastActivity >= 300000 && !isVisible) { // 5 minutes
        setIsVisible(true);
        setPosition({ 
          x: Math.random() * (window.innerWidth - 100), 
          y: window.innerHeight - 100 
        });
      }
    };

    inactivityTimerRef.current = setInterval(checkInactivity, 1000);

    return () => {
      if (inactivityTimerRef.current) {
        clearInterval(inactivityTimerRef.current);
      }
    };
  }, [lastActivity, isVisible]);

  // Duck movement logic
  useEffect(() => {
    if (!isVisible) return;

    const moveDuck = () => {
      setPosition(prev => {
        const screenWidth = window.innerWidth;
        const screenHeight = window.innerHeight;
        const duckSize = 60;
        
        // Random movement when not running
        if (!isRunning) {
          const moveDistance = 50 + Math.random() * 100;
          const angle = Math.random() * Math.PI * 2;
          
          let newX = prev.x + Math.cos(angle) * moveDistance;
          let newY = prev.y + Math.sin(angle) * moveDistance;
          
          // Keep duck within screen bounds
          newX = Math.max(0, Math.min(screenWidth - duckSize, newX));
          newY = Math.max(0, Math.min(screenHeight - duckSize, newY));
          
          // Update direction based on movement
          if (newX > prev.x) {
            setDirection('right');
          } else if (newX < prev.x) {
            setDirection('left');
          }
          
          return { x: newX, y: newY };
        }
        
        return prev;
      });
    };

    // Move duck every 2-4 seconds when not running
    const moveInterval = setInterval(moveDuck, 2000 + Math.random() * 2000);

    return () => clearInterval(moveInterval);
  }, [isVisible, isRunning]);

  // Mouse proximity detection
  useEffect(() => {
    if (!isVisible) return;

    const handleMouseMove = (e) => {
      const mouseX = e.clientX;
      const mouseY = e.clientY;
      const duckX = position.x + 30; // Duck center
      const duckY = position.y + 30;
      
      const distance = Math.sqrt(
        Math.pow(mouseX - duckX, 2) + Math.pow(mouseY - duckY, 2)
      );
      
      if (distance < 120) { // Detection radius
        setIsRunning(true);
        
        // Calculate escape direction
        const escapeAngle = Math.atan2(duckY - mouseY, duckX - mouseX);
        const escapeDistance = 150;
        
        setPosition(prev => {
          let newX = prev.x + Math.cos(escapeAngle) * escapeDistance;
          let newY = prev.y + Math.sin(escapeAngle) * escapeDistance;
          
          // Keep within bounds
          newX = Math.max(0, Math.min(window.innerWidth - 60, newX));
          newY = Math.max(0, Math.min(window.innerHeight - 60, newY));
          
          // Update direction
          setDirection(newX > prev.x ? 'right' : 'left');
          
          return { x: newX, y: newY };
        });
        
        // Stop running after a moment
        setTimeout(() => setIsRunning(false), 1000);
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    return () => document.removeEventListener('mousemove', handleMouseMove);
  }, [isVisible, position]);

  if (!isVisible) return null;

  return (
    <div 
      ref={duckRef}
      className="duck-container"
      style={{
        position: 'fixed',
        left: position.x,
        top: position.y,
        width: '60px',
        height: '60px',
        zIndex: 1000,
        pointerEvents: 'none',
        transform: direction === 'left' ? 'scaleX(-1)' : 'scaleX(1)',
        transition: 'left 0.8s ease-out, top 0.8s ease-out, transform 0.3s ease'
      }}
    >
      <div className={`duck ${isRunning ? 'duck-running' : 'duck-walking'}`}>
        🦆
      </div>
    </div>
  );
};

export default DuckAnimation;