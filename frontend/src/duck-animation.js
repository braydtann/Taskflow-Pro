import React, { useState, useEffect, useRef } from 'react';

// Duck Animation Component
const DuckAnimation = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState({ x: 100, y: window.innerHeight - 100 });
  const [isRunning, setIsRunning] = useState(false);
  const [direction, setDirection] = useState('right');
  const [lastActivity, setLastActivity] = useState(Date.now());
  const [targetPosition, setTargetPosition] = useState({ x: 100, y: window.innerHeight - 100 });
  const [isMoving, setIsMoving] = useState(false);
  const duckRef = useRef(null);
  const inactivityTimerRef = useRef(null);

  // Activity tracking
  useEffect(() => {
    const updateActivity = () => {
      setLastActivity(Date.now());
      if (isVisible) {
        setIsVisible(false);
      }
    };

    // When duck is visible, only track significant activities (not mousemove)
    // When duck is not visible, track all activities including mousemove
    const events = isVisible 
      ? ['mousedown', 'keypress', 'scroll', 'touchstart', 'click']
      : ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
    
    events.forEach(event => {
      document.addEventListener(event, updateActivity, true);
    });

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, updateActivity, true);
      });
    };
  }, [isVisible]);

  // Inactivity timer (5 minutes = 300000ms, 10 seconds for testing)
  useEffect(() => {
    const checkInactivity = () => {
      const timeSinceLastActivity = Date.now() - lastActivity;
      // Use 10 seconds for testing, 300000ms (5 minutes) for production
      const inactivityThreshold = process.env.NODE_ENV === 'development' ? 10000 : 300000;
      
      if (timeSinceLastActivity >= inactivityThreshold && !isVisible) {
        setIsVisible(true);
        const startX = Math.random() * (window.innerWidth - 100);
        const startY = window.innerHeight - 100;
        setPosition({ x: startX, y: startY });
        setTargetPosition({ x: startX, y: startY });
      }
    };

    inactivityTimerRef.current = setInterval(checkInactivity, 1000);

    return () => {
      if (inactivityTimerRef.current) {
        clearInterval(inactivityTimerRef.current);
      }
    };
  }, [lastActivity, isVisible]);

  // Enhanced duck movement logic
  useEffect(() => {
    if (!isVisible || isRunning) return;

    const moveDuck = () => {
      const screenWidth = window.innerWidth;
      const screenHeight = window.innerHeight;
      const duckSize = 60;
      const margin = 50;
      
      // Generate a new target position
      const newTargetX = margin + Math.random() * (screenWidth - duckSize - margin * 2);
      const newTargetY = margin + Math.random() * (screenHeight - duckSize - margin * 2);
      
      setTargetPosition({ x: newTargetX, y: newTargetY });
      setIsMoving(true);
      
      // Update direction based on target
      if (newTargetX > position.x) {
        setDirection('right');
      } else if (newTargetX < position.x) {
        setDirection('left');
      }
    };

    // Move duck every 3-6 seconds
    const moveInterval = setInterval(moveDuck, 3000 + Math.random() * 3000);

    return () => clearInterval(moveInterval);
  }, [isVisible, isRunning, position]);

  // Smooth movement towards target
  useEffect(() => {
    if (!isVisible || !isMoving) return;

    const smoothMove = () => {
      setPosition(prev => {
        const dx = targetPosition.x - prev.x;
        const dy = targetPosition.y - prev.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < 5) {
          setIsMoving(false);
          return targetPosition;
        }
        
        const speed = 2;
        const moveX = (dx / distance) * speed;
        const moveY = (dy / distance) * speed;
        
        return {
          x: prev.x + moveX,
          y: prev.y + moveY
        };
      });
    };

    const smoothInterval = setInterval(smoothMove, 50);
    return () => clearInterval(smoothInterval);
  }, [isVisible, isMoving, targetPosition]);

  // Enhanced mouse proximity detection
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
      
      if (distance < 150) { // Detection radius
        setIsRunning(true);
        setIsMoving(false);
        
        // Calculate multiple escape directions for more realistic movement
        const escapeAngle = Math.atan2(duckY - mouseY, duckX - mouseX);
        const escapeDistance = 200 + Math.random() * 100;
        
        // Add some randomness to make it more natural
        const angleVariation = (Math.random() - 0.5) * 0.8;
        const finalAngle = escapeAngle + angleVariation;
        
        setPosition(prev => {
          let newX = prev.x + Math.cos(finalAngle) * escapeDistance;
          let newY = prev.y + Math.sin(finalAngle) * escapeDistance;
          
          // Keep within bounds with some padding
          const padding = 30;
          newX = Math.max(padding, Math.min(window.innerWidth - 60 - padding, newX));
          newY = Math.max(padding, Math.min(window.innerHeight - 60 - padding, newY));
          
          // Update direction
          setDirection(newX > prev.x ? 'right' : 'left');
          
          return { x: newX, y: newY };
        });
        
        // Stop running after a moment
        setTimeout(() => {
          setIsRunning(false);
          setIsMoving(false);
        }, 1500);
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
        transition: isRunning ? 'transform 0.3s ease' : 'left 0.8s ease-out, top 0.8s ease-out, transform 0.3s ease'
      }}
    >
      <div className={`duck ${isRunning ? 'duck-running' : (isMoving ? 'duck-walking' : 'duck-idle')}`}>
        <div className="duck-body">
          <div className="duck-head">
            <div className="duck-beak"></div>
            <div className="duck-eye"></div>
          </div>
          <div className="duck-wing"></div>
          <div className="duck-tail"></div>
        </div>
        <div className="duck-legs">
          <div className="duck-leg duck-leg-left"></div>
          <div className="duck-leg duck-leg-right"></div>
        </div>
      </div>
    </div>
  );
};

export default DuckAnimation;