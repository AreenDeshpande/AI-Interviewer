import React from 'react';
import { Link } from 'react-router-dom';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import './LandingPage.css';

const LandingPage = () => {
  return (
    <div className="landing-container container">
      <header className="hero-section text-center">
        <h1>Welcome to AssessAI</h1>
        <p className="subtitle">Ace your next job interview with AI-powered practice and feedback.</p>
        <Link to="/signup">
          <Button variant="primary" className="mt-2">Get Started</Button>
        </Link>
      </header>

      <section className="features-section">
        <h2 className="text-center">How It Works</h2>
        <div className="features-grid">
          <Card>
    <h3>1. Sign Up</h3>
    <p>Create an account to get started with your mock interview experience.</p>
  </Card>

  <Card>
    <h3>2. Upload Resume</h3>
    <p>Upload your resume to personalize your interview questions and experience.</p>
  </Card>

  <Card>
    <h3>3. Interview</h3>
    <p>Engage in a realistic 20-minute interview with our AI interviewer.</p>
  </Card>
        </div>
      </section>
    </div>
  );
};

export default LandingPage; 