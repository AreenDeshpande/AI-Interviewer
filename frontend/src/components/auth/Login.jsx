import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Card from '../ui/Card';
import Button from '../ui/Button';
import './AuthForm.css'; // Shared CSS for Login/Signup

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    // --- Add your login API call here ---
    console.log('Login attempt:', { email });
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    // On successful login:
    // setIsAuthenticated(true); // Update global auth state
    navigate('/upload-resume'); // Redirect after login
    setLoading(false);
  };

  return (
    <div className="auth-container">
      <Card className="auth-card">
        <h2>Login</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          <Button type="submit" variant="primary" disabled={loading} className="auth-button">
            {loading ? 'Logging in...' : 'Login'}
          </Button>
        </form>
        <p className="auth-switch-link">
          Don't have an account? <Link to="/signup">Sign Up</Link>
        </p>
      </Card>
    </div>
  );
};

export default Login; 