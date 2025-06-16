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
  Grid,
  Card,
  CardContent,
  useTheme,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Computer as ComputerIcon,
  Schedule as ScheduleIcon,
  TipsAndUpdates as TipsIcon,
  ArrowForward as ArrowForwardIcon,
} from '@mui/icons-material';
import api from '../config/axios';

const Section = ({ title, items, icon, color }) => {
  const theme = useTheme();
  
  return (
    <Card 
      elevation={2} 
      sx={{ 
        height: '100%',
        transition: 'transform 0.2s',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: theme.shadows[4],
        }
      }}
    >
      <CardContent>
        <Box display="flex" alignItems="center" mb={2}>
          <Box 
            sx={{ 
              bgcolor: `${color}.light`, 
              p: 1, 
              borderRadius: 2,
              mr: 2
            }}
          >
            {icon}
          </Box>
          <Typography variant="h6" component="h2" sx={{ fontWeight: 600 }}>
            {title}
          </Typography>
        </Box>
        <List>
          {items.map((item, index) => (
            <ListItem key={index} sx={{ py: 0.5 }}>
              <ListItemIcon sx={{ minWidth: 36 }}>
                <CheckIcon color={color} />
              </ListItemIcon>
              <ListItemText 
                primary={item} 
                primaryTypographyProps={{ 
                  variant: 'body2',
                  color: 'text.secondary'
                }}
              />
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  );
};

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
    <Box sx={{ 
      minHeight: '100vh',
      background: 'linear-gradient(180deg, #f5f7fa 0%, #ffffff 100%)',
      py: 8
    }}>
      <Container maxWidth="lg">
        <Box sx={{ textAlign: 'center', mb: 8 }}>
          <Typography 
            variant="h3" 
            component="h1" 
            gutterBottom 
            sx={{ 
              fontWeight: 700,
              background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
              backgroundClip: 'text',
              textFillColor: 'transparent',
              mb: 2
            }}
          >
            Interview Instructions
          </Typography>
          <Typography 
            variant="h6" 
            color="text.secondary" 
            sx={{ 
              maxWidth: '600px', 
              mx: 'auto',
              mb: 4
            }}
          >
            Please review these instructions carefully before starting your interview
          </Typography>
        </Box>

        {instructions && (
          <Grid container spacing={4} sx={{ mb: 8 }}>
            <Grid item xs={12} md={6}>
              <Section
                title="General Rules"
                items={instructions.general_rules}
                icon={<CheckIcon sx={{ fontSize: 28, color: 'primary.main' }} />}
                color="primary"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Section
                title="Interview Format"
                items={instructions.interview_format}
                icon={<ScheduleIcon sx={{ fontSize: 28, color: 'secondary.main' }} />}
                color="secondary"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Section
                title="Technical Requirements"
                items={instructions.technical_requirements}
                icon={<ComputerIcon sx={{ fontSize: 28, color: 'info.main' }} />}
                color="info"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Section
                title="Preparation Tips"
                items={instructions.preparation_tips}
                icon={<TipsIcon sx={{ fontSize: 28, color: 'success.main' }} />}
                color="success"
              />
            </Grid>
          </Grid>
        )}

        <Box 
          display="flex" 
          justifyContent="center" 
          sx={{ 
            mt: 4,
            '& .MuiButton-root': {
              px: 4,
              py: 1.5,
              fontSize: '1.1rem'
            }
          }}
        >
          <Button
            variant="contained"
            color="primary"
            size="large"
            onClick={() => navigate('/upload-resume')}
            endIcon={<ArrowForwardIcon />}
          >
            Continue to Resume Upload
          </Button>
        </Box>
      </Container>
    </Box>
  );
};

export default InterviewInstructionsPage; 