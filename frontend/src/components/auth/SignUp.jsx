import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Card from '../ui/Card';
import Button from '../ui/Button';
import './AuthForm.css'; // Shared CSS

const SignUp = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    // --- Add your signup API call here ---
    console.log('Signup attempt:', { name, email });
     // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    // On successful signup:
    navigate('/login'); // Redirect to login after signup
    setLoading(false);
  };

  return (
    <div className="auth-container">
      <Card className="auth-card">
        <h2>Sign Up</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="name">Full Name</label>
            <input
              type="text"
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              disabled={loading}
            />
          </div>
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
             {loading ? 'Signing up...' : 'Sign Up'}
          </Button>
        </form>
        <p className="auth-switch-link">
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </Card>
    </div>
  );
};

export default SignUp; 