import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import './styles/variables.css';  // Import CSS variables

import theme from './theme';
import { AuthProvider } from './contexts/AuthContext';
import PrivateRoute from './components/PrivateRoute';

// Auth Pages
import LoginPage from './pages/auth/LoginPage.jsx';
import SignupPage from './pages/auth/SignupPage.jsx';

// Main Pages
import LandingPage from './pages/LandingPage.jsx';
import ResumeUploadPage from './pages/ResumeUploadPage.jsx';
import InterviewInstructionsPage from './pages/InterviewInstructionsPage.jsx';
import InterviewRoom from './pages/InterviewRoom.jsx';
import InterviewCompletion from './pages/InterviewCompletion';
import DashboardPage from './pages/DashboardPage.jsx';

const App = () => {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <Router>
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />

            {/* Protected Routes */}
            <Route path="/dashboard" element={
              <PrivateRoute>
                <DashboardPage />
              </PrivateRoute>
            } />
            <Route path="/upload-resume" element={
              <PrivateRoute>
                <ResumeUploadPage />
              </PrivateRoute>
            } />
            <Route path="/interview-instructions" element={
              <PrivateRoute>
                <InterviewInstructionsPage />
              </PrivateRoute>
            } />
            <Route path="/interview/:interviewId" element={
              <PrivateRoute>
                <InterviewRoom />
              </PrivateRoute>
            } />
            <Route path="/interview-completion" element={
              <PrivateRoute>
                <InterviewCompletion />
              </PrivateRoute>
            } />

            {/* Catch all route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <ToastContainer />
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App; 