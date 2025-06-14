import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Paper,
} from '@mui/material';
import {
  Description as ResumeIcon,
  VideoCall as InterviewIcon,
  Assessment as FeedbackIcon,
  Schedule as ScheduleIcon,
  ArrowForward as ArrowIcon,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

const StatCard = ({ title, value, icon, color }) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Box display="flex" alignItems="center" mb={2}>
        <Box
          sx={{
            backgroundColor: `${color}.light`,
            borderRadius: '50%',
            p: 1,
            mr: 2,
          }}
        >
          {icon}
        </Box>
        <Typography variant="h6" color="text.secondary">
          {title}
        </Typography>
      </Box>
      <Typography variant="h4" component="div" gutterBottom>
        {value}
      </Typography>
    </CardContent>
  </Card>
);

const DashboardPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Mock data - replace with actual data from your backend
  const stats = [
    {
      title: 'Resumes',
      value: '2',
      icon: <ResumeIcon sx={{ color: 'primary.main' }} />,
      color: 'primary',
    },
    {
      title: 'Interviews',
      value: '5',
      icon: <InterviewIcon sx={{ color: 'success.main' }} />,
      color: 'success',
    },
    {
      title: 'Feedback Reports',
      value: '3',
      icon: <FeedbackIcon sx={{ color: 'info.main' }} />,
      color: 'info',
    },
    {
      title: 'Upcoming',
      value: '1',
      icon: <ScheduleIcon sx={{ color: 'warning.main' }} />,
      color: 'warning',
    },
  ];

  const recentActivity = [
    {
      title: 'Resume Uploaded',
      description: 'Software Engineer Resume.pdf',
      time: '2 hours ago',
      icon: <ResumeIcon />,
    },
    {
      title: 'Interview Completed',
      description: 'Frontend Developer Interview',
      time: '1 day ago',
      icon: <InterviewIcon />,
    },
    {
      title: 'Feedback Received',
      description: 'Backend Developer Interview',
      time: '2 days ago',
      icon: <FeedbackIcon />,
    },
  ];

  return (
    <Box sx={{ p: 3 }}>
      <Box mb={4}>
        <Typography variant="h4" gutterBottom>
          Welcome back, {user?.name}!
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Here's an overview of your AI Interviewer activity
        </Typography>
      </Box>

      <Grid container spacing={3} mb={4}>
        {stats.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <StatCard {...stat} />
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">Recent Activity</Typography>
              <Button
                endIcon={<ArrowIcon />}
                onClick={() => navigate('/interviews')}
              >
                View All
              </Button>
            </Box>
            <List>
              {recentActivity.map((activity, index) => (
                <React.Fragment key={index}>
                  <ListItem>
                    <ListItemIcon>{activity.icon}</ListItemIcon>
                    <ListItemText
                      primary={activity.title}
                      secondary={
                        <Box component="span" display="flex" justifyContent="space-between">
                          <Typography variant="body2" component="span">
                            {activity.description}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" component="span">
                            {activity.time}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                  {index < recentActivity.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Quick Actions
            </Typography>
            <Box display="flex" flexDirection="column" gap={2}>
              <Button
                variant="contained"
                startIcon={<ResumeIcon />}
                onClick={() => navigate('/resumes')}
                fullWidth
              >
                Upload Resume
              </Button>
              <Button
                variant="outlined"
                startIcon={<InterviewIcon />}
                onClick={() => navigate('/interviews')}
                fullWidth
              >
                Schedule Interview
              </Button>
              <Button
                variant="outlined"
                startIcon={<FeedbackIcon />}
                onClick={() => navigate('/feedback')}
                fullWidth
              >
                View Feedback
              </Button>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage; 