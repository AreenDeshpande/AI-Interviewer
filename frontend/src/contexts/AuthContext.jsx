import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { jwtDecode } from 'jwt-decode';

// Configure axios with base URL
axios.defaults.baseURL = 'http://localhost:5000';

// Set up axios interceptor for adding token to requests
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

const AuthContext = createContext(null);

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
  const [error, setError] = useState(null);

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (token) {
          try {
            const decoded = jwtDecode(token);
            if (decoded.exp * 1000 > Date.now()) {
              // Token is valid, get user info
              const response = await axios.get('/api/me', {
                headers: { Authorization: `Bearer ${token}` }
              });
              setUser(response.data);
            } else {
              // Token expired, clear it
              localStorage.removeItem('access_token');
              setUser(null);
            }
          } catch (decodeError) {
            console.error('Token decode error:', decodeError);
            localStorage.removeItem('access_token');
            setUser(null);
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        localStorage.removeItem('access_token');
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (email, password) => {
    try {
      setError(null);
      const response = await axios.post('/api/login', {
        email,
        password
      });

      const { token, user: userData } = response.data;
      localStorage.setItem('access_token', token);
      setUser(userData);

      // Set default authorization header
      axios.defaults.headers.common.Authorization = `Bearer ${token}`;
    } catch (error) {
      setError(error.response?.data?.message || 'Login failed');
      throw error;
    }
  };

  const signup = async (userData) => {
    try {
      setError(null);
      const response = await axios.post('/api/register', userData);

      const { token, user: newUser } = response.data;
      localStorage.setItem('access_token', token);
      setUser(newUser);

      // Set default authorization header
      axios.defaults.headers.common.Authorization = `Bearer ${token}`;
    } catch (error) {
      setError(error.response?.data?.message || 'Signup failed');
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    delete axios.defaults.headers.common.Authorization;
    setUser(null);
  };

  const value = {
    user,
    loading,
    error,
    login,
    signup,
    logout
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}; 