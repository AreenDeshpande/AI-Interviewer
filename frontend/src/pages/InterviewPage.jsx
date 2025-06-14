import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Box, Button, Typography, CircularProgress, Paper } from '@mui/material';
import * as Twilio from 'twilio-video';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';

const InterviewPage = () => {
    const { interviewId } = useParams();
    const navigate = useNavigate();
    const { token } = useAuth();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [room, setRoom] = useState(null);
    const [currentQuestion, setCurrentQuestion] = useState('');
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [questions, setQuestions] = useState([]);
    const [hasMoreQuestions, setHasMoreQuestions] = useState(true);
    const [isSpeaking, setIsSpeaking] = useState(false);
    
    const videoRef = useRef(null);
    const audioRef = useRef(null);
    
    useEffect(() => {
        const initializeInterview = async () => {
            try {
                // Get token and room info
                const response = await axios.post(
                    `${process.env.REACT_APP_API_URL}/interview/${interviewId}/token`,
                    {},
                    {
                        headers: { Authorization: `Bearer ${token}` }
                    }
                );
                
                const { token: twilioToken, room_name, questions: interviewQuestions, current_question_index } = response.data;
                
                setQuestions(interviewQuestions);
                setCurrentQuestionIndex(current_question_index);
                setCurrentQuestion(interviewQuestions[current_question_index]);
                
                // Connect to Twilio room
                const room = await Twilio.connect(twilioToken, {
                    name: room_name,
                    audio: true,
                    video: true
                });
                
                setRoom(room);
                
                // Create and publish local tracks
                const videoTrack = await Twilio.createLocalVideoTrack();
                const audioTrack = await Twilio.createLocalAudioTrack();
                
                await room.localParticipant.publishTrack(videoTrack);
                await room.localParticipant.publishTrack(audioTrack);
                
                // Attach video track to DOM
                if (videoRef.current) {
                    videoTrack.attach(videoRef.current);
                }
                
                setLoading(false);
                
                // Start with first question
                if (current_question_index === 0) {
                    speakQuestion(interviewQuestions[0]);
                }
                
            } catch (err) {
                console.error('Error initializing interview:', err);
                setError(err.message);
                setLoading(false);
            }
        };
        
        initializeInterview();
        
        return () => {
            if (room) {
                room.disconnect();
            }
        };
    }, [interviewId, token]);
    
    const speakQuestion = async (question) => {
        if (!room || !room.localParticipant) return;
        
        try {
            setIsSpeaking(true);
            await room.localParticipant.say(question, { voice: 'Polly.Joanna' });
            setIsSpeaking(false);
        } catch (err) {
            console.error('Error speaking question:', err);
            setError(err.message);
            setIsSpeaking(false);
        }
    };
    
    const handleNextQuestion = async () => {
        if (!hasMoreQuestions || isSpeaking) return;
        
        try {
            const response = await axios.post(
                `${process.env.REACT_APP_API_URL}/interview/${interviewId}/next-question`,
                {},
                {
                    headers: { Authorization: `Bearer ${token}` }
                }
            );
            
            const { has_more_questions, current_question_index, question } = response.data;
            
            setHasMoreQuestions(has_more_questions);
            setCurrentQuestionIndex(current_question_index);
            setCurrentQuestion(question);
            
            if (has_more_questions) {
                speakQuestion(question);
            } else {
                // Interview completed
                navigate('/dashboard');
            }
            
        } catch (err) {
            console.error('Error moving to next question:', err);
            setError(err.message);
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
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
                <Typography color="error">{error}</Typography>
            </Box>
        );
    }
    
    return (
        <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
            <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
                <Typography variant="h5" gutterBottom>
                    Question {currentQuestionIndex + 1} of {questions.length}
                </Typography>
                <Typography variant="body1" paragraph>
                    {currentQuestion}
                </Typography>
                
                <Box display="flex" justifyContent="center" gap={2}>
                    <Button
                        variant="contained"
                        color="primary"
                        onClick={handleNextQuestion}
                        disabled={!hasMoreQuestions || isSpeaking}
                    >
                        {isSpeaking ? 'Speaking...' : hasMoreQuestions ? 'Next Question' : 'Complete Interview'}
                    </Button>
                </Box>
            </Paper>
            
            <Box sx={{ display: 'flex', gap: 2 }}>
                <Paper elevation={3} sx={{ flex: 1, p: 2 }}>
                    <Typography variant="h6" gutterBottom>Your Video</Typography>
                    <Box
                        ref={videoRef}
                        sx={{
                            width: '100%',
                            height: 300,
                            bgcolor: 'black',
                            borderRadius: 1
                        }}
                    />
                </Paper>
                
                <Paper elevation={3} sx={{ flex: 1, p: 2 }}>
                    <Typography variant="h6" gutterBottom>Interviewer</Typography>
                    <Box
                        sx={{
                            width: '100%',
                            height: 300,
                            bgcolor: 'black',
                            borderRadius: 1,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        <Typography variant="body1" color="white">
                            AI Interviewer
                        </Typography>
                    </Box>
                </Paper>
            </Box>
        </Box>
    );
};

export default InterviewPage; 