
import React from 'react';
import { Link } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  Paper,
  Avatar,
  Stack,
  Chip,
} from '@mui/material';
import {
  School as SchoolIcon,
  Psychology as PsychologyIcon,
  Analytics as AnalyticsIcon,
  Speed as SpeedIcon,
  Security as SecurityIcon,
  Support as SupportIcon,
} from '@mui/icons-material';

const FeatureCard = ({ icon, title, description }) => (
  <Card sx={{ height: '100%', transition: 'transform 0.2s', '&:hover': { transform: 'translateY(-4px)' } }}>
    <CardContent sx={{ textAlign: 'center', p: 3 }}>
      <Avatar sx={{ bgcolor: 'primary.main', mx: 'auto', mb: 2, width: 56, height: 56 }}>
        {icon}
      </Avatar>
      <Typography variant="h6" component="h3" gutterBottom>
        {title}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {description}
      </Typography>
    </CardContent>
  </Card>
);

const LandingPage = () => {
  const features = [
    {
      icon: <PsychologyIcon />,
      title: 'AI-Powered Interviews',
      description: 'Experience realistic interview scenarios powered by advanced AI technology'
    },
    {
      icon: <AnalyticsIcon />,
      title: 'Detailed Feedback',
      description: 'Get comprehensive reports on your performance with actionable insights'
    },
    {
      icon: <SpeedIcon />,
      title: 'Quick Setup',
      description: 'Upload your resume and start practicing within minutes'
    },
    {
      icon: <SecurityIcon />,
      title: 'Secure & Private',
      description: 'Your data is encrypted and handled with the highest security standards'
    },
    {
      icon: <SupportIcon />,
      title: '24/7 Available',
      description: 'Practice anytime, anywhere with our always-available AI interviewer'
    },
    {
      icon: <SchoolIcon />,
      title: 'Skill Development',
      description: 'Improve your interview skills with personalized coaching and tips'
    }
  ];

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Hero Section */}
      <Box
        sx={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          py: { xs: 8, md: 12 },
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        <Container maxWidth="lg">
          <Grid container spacing={4} alignItems="center">
            <Grid item xs={12} md={6}>
              <Typography
                variant="h2"
                component="h1"
                sx={{
                  fontWeight: 700,
                  mb: 2,
                  fontSize: { xs: '2.5rem', md: '3.5rem' }
                }}
              >
                Master Your Next Interview
              </Typography>
              <Typography
                variant="h5"
                sx={{ mb: 4, opacity: 0.9, fontWeight: 300 }}
              >
                Practice with AI-powered interviews tailored to your resume and get real-time feedback to boost your confidence.
              </Typography>
              <Stack direction="row" spacing={2} sx={{ mb: 4 }}>
                <Chip label="AI-Powered" sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }} />
                <Chip label="Personalized" sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }} />
                <Chip label="Instant Feedback" sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }} />
              </Stack>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                <Button
                  component={Link}
                  to="/signup"
                  variant="contained"
                  size="large"
                  sx={{
                    bgcolor: 'white',
                    color: 'primary.main',
                    px: 4,
                    py: 1.5,
                    '&:hover': { bgcolor: 'grey.100' }
                  }}
                >
                  Start Free Interview
                </Button>
                <Button
                  component={Link}
                  to="/login"
                  variant="outlined"
                  size="large"
                  sx={{
                    borderColor: 'white',
                    color: 'white',
                    px: 4,
                    py: 1.5,
                    '&:hover': { borderColor: 'white', bgcolor: 'rgba(255,255,255,0.1)' }
                  }}
                >
                  Sign In
                </Button>
              </Stack>
            </Grid>
            <Grid item xs={12} md={6}>
              <Paper
                sx={{
                  p: 3,
                  borderRadius: 3,
                  bgcolor: 'rgba(255,255,255,0.1)',
                  backdropFilter: 'blur(10px)',
                  border: '1px solid rgba(255,255,255,0.2)'
                }}
              >
                <Typography variant="h6" sx={{ color: 'white', mb: 2 }}>
                  🎯 Ready to get started?
                </Typography>
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                  Join thousands of job seekers who have improved their interview skills with AssessAI
                </Typography>
              </Paper>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ py: 8 }}>
        <Box sx={{ textAlign: 'center', mb: 6 }}>
          <Typography variant="h3" component="h2" gutterBottom sx={{ fontWeight: 600 }}>
            Why Choose AssessAI?
          </Typography>
          <Typography variant="h6" color="text.secondary" sx={{ maxWidth: 600, mx: 'auto' }}>
            Our AI-powered platform provides comprehensive interview practice with personalized feedback
          </Typography>
        </Box>

        <Grid container spacing={4}>
          {features.map((feature, index) => (
            <Grid item xs={12} sm={6} md={4} key={index}>
              <FeatureCard {...feature} />
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* How It Works Section */}
      <Box sx={{ bgcolor: 'grey.50', py: 8 }}>
        <Container maxWidth="lg">
          <Typography variant="h3" component="h2" align="center" gutterBottom sx={{ fontWeight: 600, mb: 6 }}>
            How It Works
          </Typography>
          <Grid container spacing={4}>
            <Grid item xs={12} md={4}>
              <Box sx={{ textAlign: 'center' }}>
                <Avatar sx={{ bgcolor: 'primary.main', mx: 'auto', mb: 2, width: 80, height: 80 }}>
                  <Typography variant="h4" sx={{ color: 'white', fontWeight: 'bold' }}>1</Typography>
                </Avatar>
                <Typography variant="h5" gutterBottom>Sign Up & Upload Resume</Typography>
                <Typography color="text.secondary">
                  Create your account and upload your resume to personalize your interview experience
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} md={4}>
              <Box sx={{ textAlign: 'center' }}>
                <Avatar sx={{ bgcolor: 'secondary.main', mx: 'auto', mb: 2, width: 80, height: 80 }}>
                  <Typography variant="h4" sx={{ color: 'white', fontWeight: 'bold' }}>2</Typography>
                </Avatar>
                <Typography variant="h5" gutterBottom>AI Interview Session</Typography>
                <Typography color="text.secondary">
                  Engage in a realistic 20-minute interview with questions tailored to your background
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} md={4}>
              <Box sx={{ textAlign: 'center' }}>
                <Avatar sx={{ bgcolor: 'success.main', mx: 'auto', mb: 2, width: 80, height: 80 }}>
                  <Typography variant="h4" sx={{ color: 'white', fontWeight: 'bold' }}>3</Typography>
                </Avatar>
                <Typography variant="h5" gutterBottom>Get Detailed Feedback</Typography>
                <Typography color="text.secondary">
                  Receive comprehensive feedback report with insights and improvement suggestions
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* CTA Section */}
      <Box sx={{ py: 8 }}>
        <Container maxWidth="md">
          <Paper
            sx={{
              p: 6,
              textAlign: 'center',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              borderRadius: 3
            }}
          >
            <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
              Ready to Ace Your Next Interview?
            </Typography>
            <Typography variant="h6" sx={{ mb: 4, opacity: 0.9 }}>
              Join thousands of successful candidates who practiced with AssessAI
            </Typography>
            <Button
              component={Link}
              to="/signup"
              variant="contained"
              size="large"
              sx={{
                bgcolor: 'white',
                color: 'primary.main',
                px: 6,
                py: 2,
                fontSize: '1.1rem',
                '&:hover': { bgcolor: 'grey.100' }
              }}
            >
              Start Your Free Interview Now
            </Button>
          </Paper>
        </Container>
      </Box>
    </Box>
  );
};

export default LandingPage;
