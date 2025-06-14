import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { jwtDecode } from 'jwt-decode';

// Configure axios with base URL
axios.defaults.baseURL = 'http://localhost:5000';

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
          const decoded = jwtDecode(token);
          if (decoded.exp * 1000 > Date.now()) {
            // Token is valid, get user info
            const response = await axios.get('/api/me', {
              headers: { Authorization: `Bearer ${token}` }
            });
            setUser(response.data);
          } else {
            // Token expired, try to refresh
            await refreshToken();
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const refreshToken = async () => {
    try {
      const refresh_token = localStorage.getItem('refresh_token');
      if (!refresh_token) throw new Error('No refresh token');

      const response = await axios.post('/api/refresh', {
        refresh_token
      });

      const { access_token } = response.data;
      localStorage.setItem('access_token', access_token);

      const decoded = jwtDecode(access_token);
      const userResponse = await axios.get('/api/me', {
        headers: { Authorization: `Bearer ${access_token}` }
      });
      setUser(userResponse.data);
    } catch (error) {
      console.error('Token refresh error:', error);
      logout();
      throw error;
    }
  };

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

      // Set up axios interceptor for token refresh
      axios.interceptors.response.use(
        (response) => response,
        async (error) => {
          const originalRequest = error.config;
          if (error.response.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
            try {
              await refreshToken();
              const newToken = localStorage.getItem('access_token');
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return axios(originalRequest);
            } catch (refreshError) {
              logout();
              return Promise.reject(refreshError);
            }
          }
          return Promise.reject(error);
        }
      );

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
    localStorage.removeItem('refresh_token');
    delete axios.defaults.headers.common.Authorization;
    setUser(null);
  };

  const value = {
    user,
    loading,
    error,
    login,
    signup,
    logout,
    refreshToken
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}; 