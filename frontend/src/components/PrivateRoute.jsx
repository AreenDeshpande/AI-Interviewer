import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';

const PrivateRoute = ({ children }) => {
  // --- Replace with your actual global authentication state check ---
  // Example: const { isAuthenticated, isLoading } = useAuth();
  const isAuthenticated = false; // <<<<----- REPLACE THIS
  const isLoading = false; // Add loading state if auth check is async

  const location = useLocation();

  if (isLoading) {
    // Optional: Show a loading spinner while checking auth
    return <div>Loading...</div>;
  }

  return isAuthenticated ? (
    children
  ) : (
    // Redirect them to the /login page, but save the current location they were
    // trying to go to when they were redirected. This allows us to send them
    // along to that page after they login, which is a nicer user experience
    // than dropping them off on the home page.
    <Navigate to="/login" state={{ from: location }} replace />
  );
};

export default PrivateRoute; 