import React from 'react'; // Removed useState as auth logic is external
import { Link, NavLink, useNavigate } from 'react-router-dom';
import Button from '../ui/Button'; // Use Button component
import './Navbar.css';

const Navbar = () => {
  const navigate = useNavigate();
  // --- Replace with your actual global authentication state ---
  // Example: const { isAuthenticated, logoutUser } = useAuth();
  const isAuthenticated = false; // <<<<----- REPLACE THIS with context or state management

  const handleLogout = () => {
    // --- Add your logout logic here (clear token, update state) ---
    // logoutUser(); // Example from context
    console.log("Logging out...");
    navigate('/login');
  };

  return (
    <nav className="navbar">
      <div className="navbar-container container">
        <Link to="/" className="navbar-logo">
          AI Interviewer
        </Link>
        <ul className="nav-menu">
          {isAuthenticated ? (
            <>
              <li className="nav-item">
                <NavLink to="/upload-resume" className={({isActive}) => "nav-links" + (isActive ? " active" : "")}>
                  Upload Resume
                </NavLink>
              </li>
              <li className="nav-item">
                <NavLink to="/schedule" className={({isActive}) => "nav-links" + (isActive ? " active" : "")}>
                  Schedule
                </NavLink>
              </li>
               <li className="nav-item">
                <NavLink to="/feedback" className={({isActive}) => "nav-links" + (isActive ? " active" : "")}>
                  Feedback
                </NavLink>
              </li>
              <li className="nav-item">
                <Button onClick={handleLogout} variant="secondary" className="logout-button">
                  Logout
                </Button>
              </li>
            </>
          ) : (
            <>
              <li className="nav-item">
                <NavLink to="/login" className={({isActive}) => "nav-links" + (isActive ? " active" : "")}>
                  Login
                </NavLink>
              </li>
              <li className="nav-item">
                 <NavLink to="/signup">
                     <Button variant="primary">Sign Up</Button>
                 </NavLink>
              </li>
            </>
          )}
        </ul>
         {/* Add Mobile Menu Toggle Here if needed */}
      </div>
    </nav>
  );
};

export default Navbar; 