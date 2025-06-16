import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Paper,
  Button
} from '@mui/material';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import { useAuth } from '../contexts/AuthContext';

const InterviewCompletion = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const handleSignOut = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <Container maxWidth="md" sx={{ py: 8 }}>
      <Paper 
        elevation={3} 
        sx={{ 
          p: 4, 
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 3
        }}
      >
        <CheckCircleOutlineIcon sx={{ fontSize: 80, color: 'success.main' }} />
        
        <Typography variant="h4" component="h1" gutterBottom>
          Interview Completed Successfully!
        </Typography>

        <Typography variant="body1" color="text.secondary" paragraph>
          Thank you for completing your interview. Your responses and the interview summary have been sent to your employer.
        </Typography>

        <Typography variant="body1" color="text.secondary" paragraph>
          You can now safely sign out of the system.
        </Typography>

        <Button
          variant="contained"
          color="primary"
          size="large"
          onClick={handleSignOut}
          sx={{ mt: 2 }}
        >
          Sign Out
        </Button>
      </Paper>
    </Container>
  );
};

export default InterviewCompletion; 