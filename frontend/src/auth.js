import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// User Context
const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('access_token'));

  // Set up axios interceptor for authentication
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  // Check if user is authenticated on app start
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem('access_token');
      if (storedToken) {
        try {
          const response = await axios.get(`${API}/auth/me`);
          setUser(response.data);
          setToken(storedToken);
        } catch (error) {
          // Token is invalid or expired
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          setToken(null);
          setUser(null);
        }
      }
      setLoading(false);
    };

    initializeAuth();
  }, []);

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { access_token, refresh_token, user: userData } = response.data;
      
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      setToken(access_token);
      setUser(userData);
      
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Login failed' 
      };
    }
  };

  const register = async (userData) => {
    try {
      const response = await axios.post(`${API}/auth/register`, userData);
      const { access_token, refresh_token, user: newUser } = response.data;
      
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      setToken(access_token);
      setUser(newUser);
      
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Registration failed' 
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  const refreshToken = async () => {
    const storedRefreshToken = localStorage.getItem('refresh_token');
    if (!storedRefreshToken) {
      logout();
      return false;
    }

    try {
      const response = await axios.post(`${API}/auth/refresh`, {
        refresh_token: storedRefreshToken
      });
      const { access_token, refresh_token: newRefreshToken } = response.data;
      
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', newRefreshToken);
      setToken(access_token);
      
      return true;
    } catch (error) {
      logout();
      return false;
    }
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    refreshToken,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Login Component
export const LoginForm = ({ onToggle }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(email, password);
    if (!result.success) {
      setError(result.error);
    }
    setLoading(false);
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h2 className="auth-title">Welcome Back to TaskFlow Pro</h2>
          <p className="auth-subtitle">Sign in to access your personal productivity dashboard</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && (
            <div className="auth-error">
              <svg fill="currentColor" viewBox="0 0 24 24" className="error-icon">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
              {error}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input
              type="email"
              className="form-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="Enter your email"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Enter your password"
            />
          </div>

          <button type="submit" className="btn btn-primary auth-btn" disabled={loading}>
            {loading ? (
              <div className="auth-loading">
                <div className="loading-spinner"></div>
                Signing In...
              </div>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Don't have an account?{' '}
            <button onClick={onToggle} className="auth-toggle-btn">
              Create Account
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

// Register Component
export const RegisterForm = ({ onToggle }) => {
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    full_name: '',
    password: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { register } = useAuth();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const validateForm = () => {
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return false;
    }
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    
    const { confirmPassword, ...userData } = formData;
    const result = await register(userData);
    
    if (!result.success) {
      setError(result.error);
    }
    setLoading(false);
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h2 className="auth-title">Join TaskFlow Pro</h2>
          <p className="auth-subtitle">Create your account and start managing tasks like a pro</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && (
            <div className="auth-error">
              <svg fill="currentColor" viewBox="0 0 24 24" className="error-icon">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
              {error}
            </div>
          )}

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input
                type="text"
                name="full_name"
                className="form-input"
                value={formData.full_name}
                onChange={handleChange}
                required
                placeholder="John Doe"
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Username</label>
              <input
                type="text"
                name="username"
                className="form-input"
                value={formData.username}
                onChange={handleChange}
                required
                placeholder="johndoe"
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input
              type="email"
              name="email"
              className="form-input"
              value={formData.email}
              onChange={handleChange}
              required
              placeholder="john@example.com"
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                type="password"
                name="password"
                className="form-input"
                value={formData.password}
                onChange={handleChange}
                required
                placeholder="At least 8 characters"
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Confirm Password</label>
              <input
                type="password"
                name="confirmPassword"
                className="form-input"
                value={formData.confirmPassword}
                onChange={handleChange}
                required
                placeholder="Confirm password"
              />
            </div>
          </div>

          <div className="password-requirements">
            <p className="requirements-title">Password must contain:</p>
            <div className="requirements-list">
              <span className={formData.password.length >= 8 ? 'requirement-met' : 'requirement-pending'}>
                • At least 8 characters
              </span>
              <span className={/[A-Z]/.test(formData.password) ? 'requirement-met' : 'requirement-pending'}>
                • One uppercase letter
              </span>
              <span className={/[a-z]/.test(formData.password) ? 'requirement-met' : 'requirement-pending'}>
                • One lowercase letter
              </span>
              <span className={/\d/.test(formData.password) ? 'requirement-met' : 'requirement-pending'}>
                • One number
              </span>
            </div>
          </div>

          <button type="submit" className="btn btn-primary auth-btn" disabled={loading}>
            {loading ? (
              <div className="auth-loading">
                <div className="loading-spinner"></div>
                Creating Account...
              </div>
            ) : (
              'Create Account'
            )}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Already have an account?{' '}
            <button onClick={onToggle} className="auth-toggle-btn">
              Sign In
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

// Main Authentication Component
export const AuthenticationPage = () => {
  const [isLogin, setIsLogin] = useState(true);

  return (
    <div className="auth-page">
      <div className="auth-background">
        <div className="auth-hero">
          <h1 className="hero-title">TaskFlow Pro</h1>
          <p className="hero-subtitle">
            Your intelligent task management platform with powerful analytics
          </p>
          <div className="hero-features">
            <div className="feature-item">
              <svg fill="currentColor" viewBox="0 0 24 24" className="feature-icon">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
              </svg>
              <span>Personal Progress Tracking</span>
            </div>
            <div className="feature-item">
              <svg fill="currentColor" viewBox="0 0 24 24" className="feature-icon">
                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
              </svg>
              <span>Advanced Analytics</span>
            </div>
            <div className="feature-item">
              <svg fill="currentColor" viewBox="0 0 24 24" className="feature-icon">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
              </svg>
              <span>Smart Scheduling</span>
            </div>
          </div>
        </div>
      </div>
      
      <div className="auth-content">
        {isLogin ? (
          <LoginForm onToggle={() => setIsLogin(false)} />
        ) : (
          <RegisterForm onToggle={() => setIsLogin(true)} />
        )}
      </div>
    </div>
  );
};

// Protected Route Component
export const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthenticationPage />;
  }

  return children;
};

// User Profile Component
export const UserProfile = () => {
  const { user, logout } = useAuth();

  return (
    <div className="user-profile-dropdown">
      <div className="profile-info">
        <div className="profile-avatar">
          {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
        </div>
        <div className="profile-details">
          <div className="profile-name">{user?.full_name}</div>
          <div className="profile-email">{user?.email}</div>
        </div>
      </div>
      
      <div className="profile-actions">
        <button onClick={logout} className="logout-btn">
          <svg fill="currentColor" viewBox="0 0 24 24" className="logout-icon">
            <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.59L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/>
          </svg>
          Sign Out
        </button>
      </div>
    </div>
  );
};