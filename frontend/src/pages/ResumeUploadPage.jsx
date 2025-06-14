import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Paper,
  Button,
  CircularProgress,
  Alert,
} from '@mui/material';
import { Upload as UploadIcon } from '@mui/icons-material';
import api from '../config/axios';
import './ResumeUploadPage.css';

const ResumeUploadPage = () => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    setError('');
    const selectedFile = e.target.files ? e.target.files[0] : null;
    if (selectedFile && selectedFile.type === "application/pdf") {
      setFile(selectedFile);
    } else {
      setFile(null);
      if (selectedFile) {
        setError('Please upload a PDF file.');
      }
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a resume file.');
      return;
    }

    setUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('resume', file);

    try {
      const response = await api.post('/upload-resume', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data) {
        navigate(`/interview/${response.data.interview_id}`);
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to upload resume. Please try again.');
      console.error("Upload error:", err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ p: 4, mt: 4 }}>
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <UploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
          <Typography variant="h4" component="h1" gutterBottom>
            Upload Your Resume
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Upload your resume (PDF format) to start your AI interview immediately.
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleUpload}>
          <Box
            sx={{
              border: '2px dashed',
              borderColor: 'primary.main',
              borderRadius: 2,
              p: 3,
              textAlign: 'center',
              mb: 3,
              bgcolor: 'primary.lightest',
              '&:hover': {
                bgcolor: 'primary.lighter',
              },
            }}
          >
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              disabled={uploading}
              style={{ display: 'none' }}
              id="resume-file"
            />
            <label htmlFor="resume-file">
              <Button
                component="span"
                variant="outlined"
                disabled={uploading}
                sx={{ mb: 2 }}
              >
                Choose PDF File
              </Button>
            </label>
            {file && (
              <Typography variant="body2" sx={{ mt: 1 }}>
                Selected file: {file.name}
              </Typography>
            )}
          </Box>

          <Box sx={{ textAlign: 'center' }}>
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={!file || uploading}
              startIcon={uploading ? <CircularProgress size={20} /> : <UploadIcon />}
            >
              {uploading ? 'Uploading...' : 'Start Interview'}
            </Button>
          </Box>
        </form>
      </Paper>
    </Container>
  );
};

export default ResumeUploadPage; 