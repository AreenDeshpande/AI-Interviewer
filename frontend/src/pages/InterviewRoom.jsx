import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Paper,
  CircularProgress,
  Alert,
  Button,
  IconButton,
  Tooltip,
} from '@mui/material';
import { 
  VideoCall as VideoCallIcon,
  Mic as MicIcon,
  MicOff as MicOffIcon,
  Videocam as VideocamIcon,
  VideocamOff as VideocamOffIcon,
  SkipNext as SkipNextIcon,
  VolumeUp as VolumeUpIcon,
  VolumeOff as VolumeOffIcon,
  Stop as StopIcon
} from '@mui/icons-material';
import * as Twilio from 'twilio-video';
import api from '../config/axios';
import './InterviewRoom.css';

const InterviewRoom = () => {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [interviewData, setInterviewData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [botStatus, setBotStatus] = useState('Connecting...');
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [questionIndex, setQuestionIndex] = useState(0);
  const roomRef = useRef(null);
  const localTrackRef = useRef(null);
  const statusPollIntervalRef = useRef(null);
  const [isNextQuestionLoading, setIsNextQuestionLoading] = useState(false);
  const [hasMoreQuestions, setHasMoreQuestions] = useState(true);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState(null);
  const speechSynthesisRef = useRef(window.speechSynthesis);
  const utteranceRef = useRef(null);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [recordedChunks, setRecordedChunks] = useState([]);
  const recordingTimeoutRef = useRef(null);


  useEffect(() => {
    const initializeInterview = async () => {
      try {
        // Get interview room data
        const response = await api.get(`/interview/${interviewId}`);
        setInterviewData(response.data);

        // Initialize Twilio video
        const { token, room_name, questions } = response.data;
        await connectToRoom(token, room_name);

        // Start polling for interview status
        startStatusPolling();

        setLoading(false);
      } catch (err) {
        setError('Failed to initialize interview room. Please try again.');
        console.error('Interview room error:', err);
        setLoading(false);
      }
    };

    initializeInterview();

    // Cleanup function
    return () => {
      if (roomRef.current) {
        roomRef.current.disconnect();
      }
      if (localTrackRef.current) {
        localTrackRef.current.stop();
      }
      if (statusPollIntervalRef.current) {
        clearInterval(statusPollIntervalRef.current);
      }
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
      }
      if (recordingTimeoutRef.current) {
        clearTimeout(recordingTimeoutRef.current);
      }
    };
  }, [interviewId]);

  useEffect(() => {
    const loadVoices = () => {
      const availableVoices = speechSynthesisRef.current.getVoices();
      setVoices(availableVoices);

      // Try to find a good female voice
      const preferredVoices = [
        'Microsoft Zira Desktop',
        'Microsoft Zira',
        'Samantha',
        'Google UK English Female',
        'Google US English Female'
      ];

      const voice = availableVoices.find(v => 
        preferredVoices.includes(v.name)
      ) || availableVoices[0];

      if (voice) {
        setSelectedVoice(voice);
      }
    };

    // Chrome loads voices asynchronously
    if (speechSynthesisRef.current.getVoices().length > 0) {
      loadVoices();
    }

    speechSynthesisRef.current.onvoiceschanged = loadVoices;

    return () => {
      speechSynthesisRef.current.onvoiceschanged = null;
      stopSpeaking();
    };
  }, []);

  const connectToRoom = async (token, roomName) => {
    try {
      // Create local audio and video tracks with fallbacks
      let localTracks = [];

      try {
        // Try to get camera and mic tracks, but don't fail if we can't
        const videoTrack = await Twilio.createLocalVideoTrack({
          name: 'camera',
          // Lower resolution to improve performance
          width: 640,
          height: 480,
        }).catch(err => {
          console.log('Could not access camera:', err);
          return null;
        });

        const audioTrack = await Twilio.createLocalAudioTrack({
          name: 'microphone',
        }).catch(err => {
          console.log('Could not access microphone:', err);
          return null;
        });

        if (videoTrack) localTracks.push(videoTrack);
        if (audioTrack) localTracks.push(audioTrack);
      } catch (err) {
        console.log('Error creating local tracks:', err);
        // Continue without local tracks
      }

      // Connect to room with or without local tracks
      const room = await Twilio.connect(token, {
        name: roomName,
        tracks: localTracks,
        // Don't require tracks to be published
        publishTrack: false,
        // Allow reconnection
        enableDominantSpeaker: true,
        dominantSpeaker: true,
        networkQuality: {
          local: 1,
          remote: 1
        }
      });

      roomRef.current = room;
      setIsConnected(true);
      console.log('Connected to room:', room.name);

      // Handle room events
      room.on('participantConnected', participant => {
        console.log('Participant connected:', participant.identity);
        setParticipants(prev => [...prev, participant]);
      });

      room.on('participantDisconnected', participant => {
        console.log('Participant disconnected:', participant.identity);
        setParticipants(prev => prev.filter(p => p.sid !== participant.sid));
      });

      // Handle track subscriptions
      room.on('trackSubscribed', (track, publication, participant) => {
        console.log('Track subscribed:', track.kind, 'from', participant.identity);
        if (track.kind === 'video') {
          setRemoteVideoTrack(track);
        } else if (track.kind === 'audio') {
          setRemoteAudioTrack(track);
        }
      });

      room.on('trackUnsubscribed', (track, publication, participant) => {
        console.log('Track unsubscribed:', track.kind, 'from', participant.identity);
        if (track.kind === 'video') {
          setRemoteVideoTrack(null);
        } else if (track.kind === 'audio') {
          setRemoteAudioTrack(null);
        }
      });

      // Handle disconnection
      room.on('disconnected', () => {
        console.log('Disconnected from room');
        setRoom(null);
        setParticipants([]);
        setRemoteVideoTrack(null);
        setRemoteAudioTrack(null);
      });

    } catch (err) {
      console.error('Error connecting to room:', err);
      // Don't set error state, just log it
      // This allows the interview to continue even without media
      console.log('Continuing without media connection');
    }
  };

  const startStatusPolling = () => {
    statusPollIntervalRef.current = setInterval(async () => {
      try {
        const response = await api.get(`/interview-status/${interviewId}`);
        const { status, current_question_index, questions } = response.data;

        if (status === 'completed') {
          clearInterval(statusPollIntervalRef.current);
          stopSpeaking();
          handleEndInterview();
          return;
        }

        if (current_question_index !== undefined && questions) {
          const newQuestionIndex = current_question_index;
          if (newQuestionIndex !== questionIndex) {
            setQuestionIndex(newQuestionIndex);
            
            // Check if we've reached the end of questions
            if (newQuestionIndex >= questions.length) {
              setHasMoreQuestions(false);
              handleEndInterview();
              return;
            }
            
            const question = questions[newQuestionIndex];
            setCurrentQuestion(question);

            // Only speak if we're not already speaking
            if (!isSpeaking) {
              speakText(question);
            }
          }
        }

      } catch (err) {
        console.error('Error polling interview status:', err);
      }
    }, 1000);
  };

  const handleEndInterview = async () => {
    try {
      // Disconnect from video room
      if (roomRef.current) {
        roomRef.current.disconnect();
      }
      if (localTrackRef.current) {
        localTrackRef.current.video.stop();
        localTrackRef.current.audio.stop();
      }

      // Stop any ongoing speech
      stopSpeaking();

      // Complete the interview and generate report
      const response = await api.post(`/interview/${interviewId}/complete`);
      
      console.log('Interview completed:', response.data);
      
      // Show success message
      if (response.data.email_sent) {
        alert('Interview completed successfully! Report has been sent via email.');
      } else {
        alert('Interview completed successfully! Report generated but email sending failed.');
      }

      // Clear authentication and redirect to login
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      navigate('/login');
    } catch (err) {
      console.error('Error ending interview:', err);
      setError('Failed to complete interview properly. Please try again.');
    }
  };

  const toggleMute = () => {
    try {
      if (isMuted) {
        speechSynthesisRef.current.resume();
      } else {
        speechSynthesisRef.current.pause();
      }
      setIsMuted(!isMuted);
    } catch (err) {
      console.error('Error toggling mute:', err);
    }
  };

  const toggleVideo = () => {
    if (localTrackRef.current?.video) {
      if (isVideoOff) {
        localTrackRef.current.video.enable();
      } else {
        localTrackRef.current.video.disable();
      }
      setIsVideoOff(!isVideoOff);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(chunks, { type: 'audio/wav' });
        await uploadRecording(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      setMediaRecorder(recorder);
      setRecordedChunks(chunks);
      recorder.start();
      setIsRecording(true);

      // Auto-stop recording after 2 minutes
      recordingTimeoutRef.current = setTimeout(() => {
        if (recorder.state === 'recording') {
          stopRecording();
        }
      }, 120000);

    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Could not start recording. Please check microphone permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.stop();
      setIsRecording(false);
      if (recordingTimeoutRef.current) {
        clearTimeout(recordingTimeoutRef.current);
      }
    }
  };

  const uploadRecording = async (audioBlob) => {
    try {
      // Convert blob to base64
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64Audio = reader.result;

        const response = await api.post(
          `/interview/${interviewId}/record-response`,
          {
            question_index: questionIndex,
            audio_blob: base64Audio
          }
        );

        console.log('Recording uploaded and transcribed:', response.data);

        // Move to next question after successful recording
        handleNextQuestion();
      };
      reader.readAsDataURL(audioBlob);
    } catch (error) {
      console.error('Error uploading recording:', error);
      alert('Failed to upload recording. Please try again.');
    }
  };

  const handleNextQuestion = async () => {
    if (isSpeaking) {
      stopSpeaking();
      return;
    }

    try {
      setIsNextQuestionLoading(true);
      const response = await api.post(`/interview/${interviewId}/next-question`);
      setHasMoreQuestions(response.data.has_more_questions);

      if (!response.data.has_more_questions) {
        setHasMoreQuestions(false);
        stopSpeaking();
        // Auto-complete interview after a short delay
        setTimeout(() => {
          handleEndInterview();
        }, 2000);
        return;
      }

      // Speak the new question
      if (response.data.question) {
        // Small delay to ensure UI updates
        setTimeout(() => {
          speakText(response.data.question);
        }, 100);
      }

    } catch (err) {
      console.error('Error moving to next question:', err);
      setError('Failed to move to next question. Please try again.');
    } finally {
      setIsNextQuestionLoading(false);
    }
  };

  const speakText = (text) => {
    if (!text || !selectedVoice) return;

    try {
      // Cancel any ongoing speech
      stopSpeaking();

      // Create a new utterance
      const utterance = new SpeechSynthesisUtterance(text);
      utteranceRef.current = utterance;

      // Configure voice settings
      utterance.voice = selectedVoice;
      utterance.rate = 0.9;  // Slightly slower for better clarity
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      // Handle speech events
      utterance.onstart = () => {
        setIsSpeaking(true);
        setBotStatus('Speaking...');
      };

      utterance.onend = () => {
        setIsSpeaking(false);
        setBotStatus('Ready');
        utteranceRef.current = null;
      };

      utterance.onerror = (event) => {
        console.error('Speech synthesis error:', event);
        setIsSpeaking(false);
        setBotStatus('Error speaking');
        utteranceRef.current = null;

        // Try to recover from error
        if (event.error === 'interrupted' || event.error === 'canceled') {
          // These are expected errors when stopping speech
          return;
        }

        // For other errors, try to speak again after a short delay
        setTimeout(() => {
          if (text === currentQuestion) {
            speakText(text);
          }
        }, 1000);
      };

      // Speak the text
      speechSynthesisRef.current.speak(utterance);

    } catch (err) {
      console.error('Error in speakText:', err);
      setIsSpeaking(false);
      setBotStatus('Error speaking');
    }
  };

  const stopSpeaking = () => {
    try {
      if (utteranceRef.current) {
        speechSynthesisRef.current.cancel();
        utteranceRef.current = null;
      }
      setIsSpeaking(false);
      setBotStatus('Ready');
    } catch (err) {
      console.error('Error stopping speech:', err);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
        <Button
          variant="contained"
          onClick={() => navigate('/dashboard')}
          startIcon={<VideoCallIcon />}
        >
          Return to Dashboard
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h5" gutterBottom>
          AI Interview Session
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Interview ID: {interviewId}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Bot Status: {botStatus}
        </Typography>
      </Paper>

      {/* Single video screen */}
      <Paper
        elevation={2}
        sx={{
          width: '100%',
          height: '480px',
          overflow: 'hidden',
          bgcolor: 'black',
          position: 'relative',
          mb: 3
        }}
      >
        <div id="local-media" className="video-container" />
        {currentQuestion && (
          <Box sx={{ 
            position: 'absolute', 
            bottom: 0, 
            left: 0, 
            right: 0, 
            bgcolor: 'rgba(0,0,0,0.7)', 
            color: 'white',
            p: 2
          }}>
            <Typography variant="subtitle1">
              Question {questionIndex + 1}: {currentQuestion}
            </Typography>
          </Box>
        )}

        {/* Video controls overlay */}
        <Box sx={{ 
          position: 'absolute', 
          bottom: 16, 
          left: '50%', 
          transform: 'translateX(-50%)',
          display: 'flex',
          gap: 2,
          bgcolor: 'rgba(0,0,0,0.5)',
          p: 1,
          borderRadius: 2
        }}>
          <Tooltip title={isMuted ? "Unmute" : "Mute"}>
            <IconButton 
              onClick={toggleMute}
              sx={{ color: 'white' }}
            >
              {isMuted ? <MicOffIcon /> : <MicIcon />}
            </IconButton>
          </Tooltip>
          <Tooltip title={isVideoOff ? "Turn on camera" : "Turn off camera"}>
            <IconButton 
              onClick={toggleVideo}
              sx={{ color: 'white' }}
            >
              {isVideoOff ? <VideocamOffIcon /> : <VideocamIcon />}
            </IconButton>
          </Tooltip>
        </Box>
      </Paper>

      {/* Recording Controls */}
      {isConnected && currentQuestion && (
        <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Response Recording
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Click "Start Recording" to record your response to the current question.
          </Typography>
          <Box display="flex" gap={2} alignItems="center">
            {!isRecording ? (
              <Button
                variant="contained"
                color="error"
                onClick={startRecording}
                startIcon={<MicIcon />}
                disabled={isNextQuestionLoading}
              >
                Start Recording
              </Button>
            ) : (
              <Button
                variant="contained"
                color="primary"
                onClick={stopRecording}
                startIcon={<StopIcon />}
              >
                Stop Recording
              </Button>
            )}
            {isRecording && (
              <Typography variant="body2" color="error">
                Recording... (Click Stop when finished)
              </Typography>
            )}
          </Box>
        </Paper>
      )}


      {/* Controls */}
      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={handleNextQuestion}
          disabled={isNextQuestionLoading || !hasMoreQuestions}
          startIcon={isNextQuestionLoading ? <CircularProgress size={20} /> : <SkipNextIcon />}
          size="large"
          sx={{ minWidth: 200 }}
        >
          {isSpeaking ? "Stop" : isNextQuestionLoading ? "Loading..." : "Next Question"}
        </Button>

        <Button
          variant="contained"
          color="error"
          onClick={handleEndInterview}
          disabled={!isConnected}
          size="large"
        >
          End Interview
        </Button>
      </Box>
    </Container>
  );
};

export default InterviewRoom;