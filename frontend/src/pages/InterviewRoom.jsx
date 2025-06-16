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
  // Add a new ref for the local video container
  const localVideoRef = useRef(null);
  // Add this state to track camera availability
  const [isCameraAvailable, setIsCameraAvailable] = useState(true);
  const [participants, setParticipants] = useState([]);
  const [remoteVideoTrack, setRemoteVideoTrack] = useState(null);
  const [remoteAudioTrack, setRemoteAudioTrack] = useState(null);
  const [room, setRoom] = useState(null);

  // Create refs for remote media containers
  const remoteVideoRef = useRef(null);
  const remoteAudioRef = useRef(null);


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
      console.log('Cleaning up interview room...');
      
      // Disconnect from room
      if (roomRef.current) {
        roomRef.current.disconnect();
        console.log('Disconnected from Twilio room');
      }
      
      // Stop local tracks
      if (localTrackRef.current) {
        if (localTrackRef.current.video) {
          localTrackRef.current.video.stop();
          console.log('Stopped local video track');
        }
        if (localTrackRef.current.audio) {
          localTrackRef.current.audio.stop();
          console.log('Stopped local audio track');
        }
      }
      
      // Detach remote tracks
      if (remoteVideoTrack) {
        remoteVideoTrack.detach().forEach(element => element.remove());
      }
      if (remoteAudioTrack) {
        remoteAudioTrack.detach().forEach(element => element.remove());
      }
      
      // Clear intervals and timeouts
      if (statusPollIntervalRef.current) {
        clearInterval(statusPollIntervalRef.current);
      }
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
      }
      if (recordingTimeoutRef.current) {
        clearTimeout(recordingTimeoutRef.current);
      }
      
      // Stop any speech synthesis
      stopSpeaking();
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
      let localVideoTrack = null;
      let localAudioTrack = null;

      try {
        // Try to get camera and mic tracks, but don't fail if we can't
        localVideoTrack = await Twilio.createLocalVideoTrack({
          name: 'camera',
          // Lower resolution to improve performance
          width: 640,
          height: 480,
        }).catch(err => {
          console.log('Could not access camera:', err);
          setIsCameraAvailable(false);
          return null;
        });

        localAudioTrack = await Twilio.createLocalAudioTrack({
          name: 'microphone',
        }).catch(err => {
          console.log('Could not access microphone:', err);
          return null;
        });

        if (localVideoTrack) {
          localTracks.push(localVideoTrack);
          
          // Attach the video track to the DOM element
          if (localVideoRef.current) {
            // Clear any existing content
            localVideoRef.current.innerHTML = '';
            
            // Create a new video element and attach the track to it
            const videoElement = localVideoTrack.attach();
            videoElement.style.width = '100%';
            videoElement.style.height = '100%';
            videoElement.style.objectFit = 'cover';
            
            // Add the video element to the container
            localVideoRef.current.appendChild(videoElement);
            
            console.log('Local video track attached to DOM');
          }
        }
        
        if (localAudioTrack) localTracks.push(localAudioTrack);
        
        // Store local tracks for later use (muting, etc.)
        localTrackRef.current = {
          video: localVideoTrack,
          audio: localAudioTrack
        };
        
      } catch (err) {
        console.log('Error creating local tracks:', err);
        // Continue without local tracks
      }

      // Connect to room with or without local tracks
      const room = await Twilio.connect(token, {
        name: roomName,
        tracks: localTracks,
        // Publish tracks if available
        automaticSubscription: true
      });

      roomRef.current = room;
      setRoom(room);
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
          // Attach video track to DOM if container exists
          if (remoteVideoRef.current) {
            remoteVideoRef.current.innerHTML = '';
            const videoElement = track.attach();
            videoElement.style.width = '100%';
            videoElement.style.height = '100%';
            remoteVideoRef.current.appendChild(videoElement);
          }
        } else if (track.kind === 'audio') {
          setRemoteAudioTrack(track);
          // Attach audio track to DOM
          if (remoteAudioRef.current) {
            remoteAudioRef.current.innerHTML = '';
            const audioElement = track.attach();
            remoteAudioRef.current.appendChild(audioElement);
          }
        }
      });

      room.on('trackUnsubscribed', (track, publication, participant) => {
        console.log('Track unsubscribed:', track.kind, 'from', participant.identity);
        // Detach the track element
        track.detach().forEach(element => element.remove());
        
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
      console.log('Starting audio recording...');
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000
        }
      });
      
      console.log('Got media stream');
      
      // Use webm format as it's more widely supported
      const options = {
        mimeType: 'audio/webm;codecs=opus'
      };
      
      // Fallback if webm is not supported
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options.mimeType = 'audio/webm';
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
          options.mimeType = 'audio/wav';
          if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            delete options.mimeType; // Use default
          }
        }
      }
      
      console.log('Using MIME type:', options.mimeType || 'default');
      
      const recorder = new MediaRecorder(stream, options);
      const chunks = [];

      recorder.ondataavailable = (event) => {
        console.log('Data available, size:', event.data.size);
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onstop = async () => {
        console.log('Recording stopped, chunks:', chunks.length);
        const mimeType = recorder.mimeType || 'audio/webm';
        const audioBlob = new Blob(chunks, { type: mimeType });
        console.log('Created blob, size:', audioBlob.size, 'type:', audioBlob.type);
        
        if (audioBlob.size > 0) {
          await uploadRecording(audioBlob);
        } else {
          console.error('No audio data recorded');
          alert('No audio was recorded. Please try again.');
        }
        
        stream.getTracks().forEach(track => track.stop());
      };

      recorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
        alert('Recording error occurred. Please try again.');
      };

      setMediaRecorder(recorder);
      setRecordedChunks(chunks);
      
      console.log('Starting recorder...');
      recorder.start(1000); // Collect data every second
      setIsRecording(true);

      // Auto-stop recording after 2 minutes
      recordingTimeoutRef.current = setTimeout(() => {
        console.log('Auto-stopping recording after timeout');
        if (recorder.state === 'recording') {
          stopRecording();
        }
      }, 120000);

    } catch (error) {
      console.error('Error starting recording:', error);
      alert(`Could not start recording: ${error.message}. Please check microphone permissions.`);
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
      console.log('Uploading audio blob, size:', audioBlob.size, 'type:', audioBlob.type);
      
      // Convert blob to base64
      const reader = new FileReader();
      reader.onloadend = async () => {
        try {
          const base64Audio = reader.result;
          console.log('Base64 audio length:', base64Audio.length);

          const response = await api.post(
            `/interview/${interviewId}/record-response`,
            {
              question_index: questionIndex,
              audio_blob: base64Audio
            }
          );

          console.log('Recording uploaded and transcribed:', response.data);
          
          // Show transcription to user for verification
          if (response.data.transcription) {
            const transcriptionPreview = response.data.transcription.length > 100 
              ? response.data.transcription.substring(0, 100) + '...' 
              : response.data.transcription;
            
            console.log('Transcription:', transcriptionPreview);
            // You could show this in a toast notification if desired
          }

          // Move to next question after successful recording
          setTimeout(() => {
            handleNextQuestion();
          }, 1000); // Small delay to let user see the result
          
        } catch (uploadError) {
          console.error('Error in upload request:', uploadError);
          alert(`Failed to upload recording: ${uploadError.response?.data?.message || uploadError.message}`);
        }
      };
      
      reader.onerror = (error) => {
        console.error('Error reading audio file:', error);
        alert('Failed to process audio file. Please try again.');
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

  // Update the speakText function to use the correct voice
  const speakText = (text) => {
    if (!text || !selectedVoice) return;

    try {
      console.log("Speaking text:", text);
      
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
        console.log("Speech started");
        setIsSpeaking(true);
        setBotStatus('Speaking...');
      };

      utterance.onend = () => {
        console.log("Speech ended");
        setIsSpeaking(false);
        setBotStatus('Ready');
        utteranceRef.current = null;
      };

      utterance.onerror = (event) => {
        console.error('Speech synthesis error:', event);
        setIsSpeaking(false);
        setBotStatus('Error speaking');
        utteranceRef.current = null;
      };

      // Speak the text
      speechSynthesisRef.current.speak(utterance);
    } catch (err) {
      console.error('Error in speakText:', err);
      setIsSpeaking(false);
      setBotStatus('Error speaking');
    }
  };

  // Make sure questions are automatically spoken when they change
  useEffect(() => {
    if (currentQuestion && !isSpeaking) {
      console.log("Auto-speaking question:", currentQuestion);
      speakText(currentQuestion);
    }
  }, [currentQuestion, selectedVoice]);

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

  // Add this function to your component
  const testCameraAccess = async () => {
    try {
      setBotStatus('Testing camera access...');
      
      // Request camera access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: true, 
        audio: true 
      });
      
      console.log('Camera access granted!', stream);
      
      // Create a temporary video element to test the stream
      const tempVideo = document.createElement('video');
      tempVideo.srcObject = stream;
      tempVideo.autoplay = true;
      
      // Wait for video to start playing
      await new Promise(resolve => {
        tempVideo.onplaying = resolve;
      });
      
      // Stop the stream after testing
      stream.getTracks().forEach(track => track.stop());
      
      alert('Camera is working! Video stream created successfully.');
      setBotStatus('Camera test passed');
      setIsCameraAvailable(true);
    } catch (error) {
      console.error('Camera test failed:', error);
      alert(`Camera test failed: ${error.message}. Please check your camera permissions.`);
      setBotStatus('Camera test failed');
      setIsCameraAvailable(false);
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
        {/* This is the container for the local video */}
        <div 
          ref={localVideoRef} 
          className="video-container" 
          style={{
            width: '100%',
            height: '100%',
            position: 'relative'
          }}
        />
        
        {/* Add these somewhere in your Paper element that contains video */}
        <div 
          ref={remoteVideoRef} 
          className="remote-video" 
          style={{
            display: remoteVideoTrack ? 'block' : 'none',
            position: 'absolute',
            width: '100%',
            height: '100%',
            top: 0,
            left: 0,
            zIndex: 5
          }}
        />
        <div ref={remoteAudioRef} style={{ display: 'none' }}></div>

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

      {/* Alert for camera availability */}
      {!isCameraAvailable && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Camera access is not available. Please check your camera permissions and refresh the page.
        </Alert>
      )}

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

      {/* Add this button somewhere in your UI for debugging */}
      <Button 
        variant="outlined" 
        onClick={testCameraAccess} 
        startIcon={<VideocamIcon />}
        sx={{ mt: 2 }}
      >
        Test Camera
      </Button>
    </Container>
  );
};

export default InterviewRoom;