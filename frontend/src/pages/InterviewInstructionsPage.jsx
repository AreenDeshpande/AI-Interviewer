import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Button,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Computer as ComputerIcon,
  Schedule as ScheduleIcon,
  TipsAndUpdates as TipsIcon,
} from '@mui/icons-material';
import api from '../config/axios';

const Section = ({ title, items, icon }) => (
  <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
    <Box display="flex" alignItems="center" mb={2}>
      {icon}
      <Typography variant="h6" component="h2" sx={{ ml: 1 }}>
        {title}
      </Typography>
    </Box>
    <List>
      {items.map((item, index) => (
        <ListItem key={index}>
          <ListItemIcon>
            <CheckIcon color="primary" />
          </ListItemIcon>
          <ListItemText primary={item} />
        </ListItem>
      ))}
    </List>
  </Paper>
);

const InterviewInstructionsPage = () => {
  const [instructions, setInstructions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchInstructions = async () => {
      try {
        const response = await api.get('/interview-instructions');
        setInstructions(response.data);
      } catch (err) {
        setError('Failed to load interview instructions. Please try again later.');
        console.error('Error fetching instructions:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchInstructions();
  }, []);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="80vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom align="center">
        Interview Instructions
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" paragraph align="center">
        Please review these instructions carefully before starting your interview
      </Typography>

      {instructions && (
        <>
          <Section
            title="General Rules"
            items={instructions.general_rules}
            icon={<CheckIcon color="primary" sx={{ fontSize: 28 }} />}
          />
          <Section
            title="Interview Format"
            items={instructions.interview_format}
            icon={<ScheduleIcon color="primary" sx={{ fontSize: 28 }} />}
          />
          <Section
            title="Technical Requirements"
            items={instructions.technical_requirements}
            icon={<ComputerIcon color="primary" sx={{ fontSize: 28 }} />}
          />
          <Section
            title="Preparation Tips"
            items={instructions.preparation_tips}
            icon={<TipsIcon color="primary" sx={{ fontSize: 28 }} />}
          />
        </>
      )}

      <Box display="flex" justifyContent="center" mt={4}>
        <Button
          variant="contained"
          color="primary"
          size="large"
          onClick={() => navigate('/upload-resume')}
        >
          Upload Resume
        </Button>
      </Box>
    </Container>
  );
};

export default InterviewInstructionsPage; 