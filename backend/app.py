import json
import os
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, send_file, url_for, render_template
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import jwt
import bcrypt
from functools import wraps
import uuid
from werkzeug.utils import secure_filename
import shutil
import openai
from PyPDF2 import PdfReader
from twilio.rest import Client
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VideoGrant
from twilio.base.exceptions import TwilioRestException
import asyncio
import websockets
import threading
import time
import boto3
import tempfile
import speech_recognition as sr
import pydub
from pydub import AudioSegment
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
import io


# Load environment variables
load_dotenv()

# Validate required environment variables
required_env_vars = [
    'OPENAI_API_KEY',
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN',
    'TWILIO_API_KEY',
    'TWILIO_API_SECRET',
    'MONGODB_URI',
    'JWT_SECRET_KEY'
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(missing_vars)}\n"
        "Please check your .env file and ensure all required variables are set."
    )

# Initialize OpenAI client
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize Twilio client
twilio_client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)

# Twilio configuration
TWILIO_API_KEY = os.getenv('TWILIO_API_KEY')
TWILIO_API_SECRET = os.getenv('TWILIO_API_SECRET')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')

# Bot configuration
BOT_NAME = "ASSESS AI"
BOT_AVATAR = "https://your-domain.com/bot-avatar.png"  # Replace with your bot avatar URL

app = Flask(__name__)
# Configure CORS to allow requests from the frontend
CORS(app, resources={
    r"/*": {  # Allow all routes
        "origins": ["http://localhost:5173"],  # Vite's default port
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# MongoDB setup
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/ai_interviewer'))
db = client.ai_interviewer

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# JWT configuration
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-here')

# Authentication decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            token = token.split(' ')[1]  # Remove 'Bearer ' prefix
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = db.users.find_one({'_id': ObjectId(data['user_id'])})
            if not current_user:
                return jsonify({'message': 'Invalid token!'}), 401
        except:
            return jsonify({'message': 'Invalid token!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def extract_text_from_pdf(file_path):
    """Extract text from PDF file."""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return None

def parse_resume_with_openai(resume_text):
    """Parse resume using OpenAI to extract key information as a simple array."""
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """Extract key information from the resume. 
                Return ONLY an array of strings, with each string containing one piece of information.
                Include skills, experience highlights, education, and projects.
                Example format:
                Skills: JavaScript, React, Node.js
                Experience: Senior Developer at Tech Corp (2020-2023)
                Education: BS Computer Science, University of Tech
                Project: Built e-commerce platform using MERN stack"""},
                {"role": "user", "content": f"Parse this resume and extract key information:\n\n{resume_text}"}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        # Split the response into an array of strings
        return response.choices[0].message.content.strip().split('\n')
    except Exception as e:
        print(f"Error parsing resume with OpenAI: {str(e)}")
        return None

def generate_interview_questions(resume_text):
    """Generate a fixed set of interview questions for testing."""
    # Comment out the OpenAI parsing and question generation
    """
    try:
        # Parse resume with OpenAI
        resume_data = parse_resume_with_openai(resume_text)
        if not resume_data:
            raise Exception("Failed to parse resume")
        
        # Generate interview questions
        questions = generate_interview_questions(resume_data)
        if not questions:
            raise Exception("Failed to generate interview questions")
        
        return questions
    except Exception as e:
        print(f"Error generating interview questions: {str(e)}")
        return None
    """
    
    # Return a fixed set of interview questions for testing
    return [
        "Tell me about yourself and your background in software development.",
        "What programming languages are you most comfortable with, and why?",
        "Describe a challenging project you worked on and how you overcame obstacles.",
        "How do you stay updated with the latest technologies and industry trends?",
        "Where do you see yourself in your career in the next 5 years?"
    ]

def get_next_question(interview_id, current_question_index):
    """Get the next question for the interview."""
    try:
        interview = db.interviews.find_one({'_id': ObjectId(interview_id)})
        if not interview or 'questions' not in interview:
            return None
        
        questions = interview['questions']
        if current_question_index >= len(questions):
            return None
        
        return questions[current_question_index]
    except Exception as e:
        print(f"Error getting next question: {str(e)}")
        return None

def transcribe_audio(audio_file_path):
    """Transcribe audio file to text using speech recognition."""
    try:
        # Initialize recognizer with adjusted settings
        r = sr.Recognizer()
        r.energy_threshold = 300
        r.dynamic_energy_threshold = True
        r.pause_threshold = 0.8
        r.operation_timeout = None
        r.phrase_threshold = 0.3
        r.non_speaking_duration = 0.8
        
        # Convert audio to wav format if needed
        audio = AudioSegment.from_file(audio_file_path)
        
        # Normalize audio levels
        audio = audio.normalize()
        
        # Ensure proper format for speech recognition
        audio = audio.set_frame_rate(16000).set_channels(1)
        
        wav_path = audio_file_path.replace('.mp3', '.wav').replace('.m4a', '.wav').replace('.webm', '.wav')
        audio.export(wav_path, format="wav")
        
        # Transcribe audio with multiple attempts
        with sr.AudioFile(wav_path) as source:
            # Adjust for ambient noise
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = r.record(source)
            
            # Try Google Speech Recognition first
            try:
                text = r.recognize_google(audio_data, language='en-US')
                print(f"Google Speech Recognition result: {text}")
                return text
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand audio")
                return "Could not understand audio - please speak more clearly"
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")
                # Fallback to basic text if service is unavailable
                return "Audio was recorded but transcription service is unavailable"
            
    except Exception as e:
        print(f"Error transcribing audio: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return f"Error during transcription: {str(e)}"
    finally:
        # Clean up temporary wav file
        try:
            if 'wav_path' in locals() and wav_path != audio_file_path and os.path.exists(wav_path):
                os.remove(wav_path)
        except Exception as cleanup_error:
            print(f"Error cleaning up temp file: {cleanup_error}")

def generate_interview_report(interview_data):
    """Generate interview report using OpenAI."""
    try:
        # Prepare interview data for analysis
        qa_pairs = []
        questions = interview_data.get('questions', [])
        responses = interview_data.get('responses', [])
        
        # Create Q&A pairs
        for i, question in enumerate(questions):
            # Find corresponding response
            response = None
            for r in responses:
                if r.get('question_index') == i:
                    response = r
                    break
            
            answer = response.get('transcription', 'No response recorded') if response else 'No response recorded'
            qa_pairs.append(f"Q{i+1}: {question}\nA{i+1}: {answer}")
        
        interview_text = "\n\n".join(qa_pairs)
        
        # Generate report using OpenAI
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """You are an expert interview assessor. Analyze the interview responses and provide a comprehensive evaluation report. 

Structure your response as follows:
1. CANDIDATE OVERVIEW
2. STRENGTHS (list key strengths with examples)
3. AREAS FOR IMPROVEMENT (list weaknesses with specific feedback)
4. TECHNICAL SKILLS ASSESSMENT
5. COMMUNICATION SKILLS
6. OVERALL RECOMMENDATION (Recommend/Consider/Not Recommend)
7. SCORE (out of 10)

Be professional, constructive, and specific in your feedback. If responses are missing or incomplete, note this and provide guidance on what additional information would be helpful."""},
                {"role": "user", "content": f"Please analyze this interview and provide a detailed assessment report:\n\n{interview_text}"}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating report with OpenAI: {str(e)}")
        # Return a fallback report if OpenAI fails
        questions = interview_data.get('questions', [])
        responses = interview_data.get('responses', [])
        
        fallback_report = f"""
INTERVIEW ASSESSMENT REPORT

CANDIDATE OVERVIEW:
The candidate participated in an AI-conducted interview with {len(questions)} questions.
{len(responses)} responses were recorded.

TECHNICAL ASSESSMENT:
Unable to perform automated analysis due to system limitations.

COMMUNICATION SKILLS:
Manual review required for assessment.

RESPONSES SUMMARY:
"""
        
        for i, question in enumerate(questions):
            response = next((r for r in responses if r.get('question_index') == i), None)
            answer = response.get('transcription', 'No response') if response else 'No response'
            fallback_report += f"\nQ{i+1}: {question}\nA{i+1}: {answer[:100]}{'...' if len(answer) > 100 else ''}\n"
        
        fallback_report += "\n\nRECOMMENDATION: Manual review required\nSCORE: Pending detailed analysis"
        
        return fallback_report

def create_pdf_report(report_content, candidate_name="Candidate"):
    """Create PDF report from text content."""
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
        )
        
        # Build PDF content
        story = []
        story.append(Paragraph(f"Interview Assessment Report - {candidate_name}", title_style))
        story.append(Spacer(1, 20))
        
        # Split report into sections and format
        sections = report_content.split('\n')
        for section in sections:
            if section.strip():
                if section.strip().isupper() and len(section.strip()) < 50:
                    story.append(Paragraph(section.strip(), heading_style))
                else:
                    story.append(Paragraph(section.strip(), body_style))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Error creating PDF: {str(e)}")
        return None

def send_report_email(report_pdf, candidate_name="Candidate", recipient_email="areendeshpande@gmail.com"):
    """Send interview report via email."""
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f"Interview Assessment Report - {candidate_name}"
        msg['From'] = 'areendeshpande@gmail.com'
        msg['To'] = recipient_email
        
        # Email body
        body = f"""
        Dear Hiring Manager,
        
        Please find attached the comprehensive interview assessment report for {candidate_name}.
        
        The report includes:
        - Candidate overview
        - Strengths and areas for improvement
        - Technical and communication skills assessment
        - Overall recommendation and scoring
        
        This report was generated automatically by AssessAI based on the candidate's interview responses.
        
        Best regards,
        AssessAI System
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF report
        if report_pdf:
            part = MIMEApplication(report_pdf.getvalue(), Name=f"{candidate_name}_Interview_Report.pdf")
            part['Content-Disposition'] = f'attachment; filename="{candidate_name}_Interview_Report.pdf"'
            msg.attach(part)
        
        # Send email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login('areendeshpande@gmail.com', os.getenv("GMAIL_PASS"))
            smtp.send_message(msg)
            print(f"Report sent successfully to {recipient_email}")
            return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def generate_twilio_token(identity, room_name):
    """Generate Twilio Access Token for video room."""
    try:
        # Create an Access Token
        token = AccessToken(
            TWILIO_ACCOUNT_SID,
            TWILIO_API_KEY,
            TWILIO_API_SECRET,
            identity=identity
        )
        
        # Create a Video grant and add to token
        video_grant = VideoGrant(room=room_name)
        token.add_grant(video_grant)
        
        # Generate the token and convert to string
        return str(token.to_jwt())
    except Exception as e:
        print(f"Error generating Twilio token: {str(e)}")
        raise Exception("Failed to generate access token for video room")

def create_interview_room(interview_id, user_id):
    """Create a new Twilio video room for the interview."""
    try:
        # Create a unique room name using interview_id
        room_name = f"interview-{interview_id}"
        
        # Create the room using Twilio client
        room = twilio_client.video.v1.rooms.create(
            unique_name=room_name,
            type='group',  # Using 'group' type as it's currently supported
            record_participants_on_connect=True,
            status_callback='https://your-domain.com/status-callback',  # Replace with your callback URL
            status_callback_method='POST'
        )
        
        # Generate tokens for both user and bot
        user_token = generate_twilio_token(f"user-{user_id}", room_name)
        bot_token = generate_twilio_token(f"bot-{interview_id}", room_name)
        
        return {
            'room_name': room_name,
            'room_sid': room.sid,
            'user_token': user_token,
            'bot_token': bot_token
        }
    except Exception as e:
        print(f"Error creating interview room: {str(e)}")
        raise Exception("Failed to create video interview room")

class InterviewManager:
    def __init__(self, room_name, interview_id, questions):
        self.room_name = room_name
        self.interview_id = interview_id
        self.questions = questions
        self.current_question_index = 0
        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
    @classmethod
    def from_interview(cls, interview):
        """Create an InterviewManager instance from interview data."""
        return cls(
            room_name=interview['room_name'],
            interview_id=interview['interview_id'],
            questions=interview['questions']
        )
        
    def start(self):
        """Initialize the interview room."""
        try:
            print(f"Starting interview in room: {self.room_name}")
            
            # Ensure room exists
            try:
                room = self.client.video.v1.rooms(self.room_name).fetch()
            except TwilioRestException as e:
                if e.code == 20404:  # Room not found
                    # Create the room if it doesn't exist
                    room = self.client.video.v1.rooms.create(
                        unique_name=self.room_name,
                        type='group',
                        record_participants_on_connect=True
                    )
                    print(f"Created new room: {self.room_name}")
                else:
                    raise
            
            # Update interview status
            self.update_interview_status('ready')
            print("Interview room is ready")
            
            return True
            
        except Exception as e:
            print(f"Error starting interview: {str(e)}")
            self.update_interview_status('error', {'error_message': str(e)})
            return False
            
    def update_interview_status(self, status, data=None):
        """Update the interview status in the database."""
        try:
            update_data = {
                'status': status,
                'current_question_index': self.current_question_index
            }
            if data:
                update_data.update(data)
                
            db.interviews.update_one(
                {'interview_id': self.interview_id},
                {'$set': update_data}
            )
            print(f"Updated interview status to: {status}")
            
        except Exception as e:
            print(f"Error updating interview status: {str(e)}")

# User routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if db.users.find_one({'email': data['email']}):
        return jsonify({'message': 'Email already exists'}), 400
    
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
    
    user = {
        'email': data['email'],
        'password': hashed_password,
        'name': data.get('name', ''),
        'created_at': datetime.now(timezone.utc)
    }
    
    result = db.users.insert_one(user)
    user['_id'] = str(result.inserted_id)
    user.pop('password')
    
    return jsonify(user), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = db.users.find_one({'email': data['email']})
    
    if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), user['password']):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    token = jwt.encode({
        'user_id': str(user['_id']),
        'exp': datetime.now(timezone.utc) + timedelta(days=1)
    }, app.config['SECRET_KEY'])
    
    return jsonify({
        'token': token,
        'user': {
            'id': str(user['_id']),
            'email': user['email'],
            'name': user.get('name', '')
        }
    })

# Resume routes
@app.route('/upload-resume', methods=['POST'])
@token_required
def upload_resume(current_user):
    """Handle resume upload and create interview room with simulated processing."""
    if 'resume' not in request.files:
        return jsonify({'error': 'No resume file provided'}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    try:
        # Simulate resume processing delay
        time.sleep(2)  # Simulate 2 seconds of processing
        
        # Get the fixed interview questions
        questions = generate_interview_questions("")
        
        # Create interview record with simulated resume data
        interview_id = str(uuid.uuid4())
        interview = {
            '_id': ObjectId(),  # MongoDB document ID
            'interview_id': interview_id,  # Our custom interview ID
            'user_id': current_user['_id'],
            'resume_filename': file.filename,
            'resume_processed': True,
            'questions': questions,
            'status': 'scheduled',
            'created_at': datetime.now(timezone.utc),
            'scheduled_at': datetime.now(timezone.utc),
            'processing_time': '2 seconds',
            'current_question_index': 0  # Add initial question index
        }
        
        # Insert into database
        result = db.interviews.insert_one(interview)
        print(f"Created interview with ID: {interview_id}")
        
        # Create video interview room
        room_details = create_interview_room(interview_id, str(current_user['_id']))
        
        # Store the token in the interview document
        db.interviews.update_one(
            {'interview_id': interview_id},
            {'$set': {'candidate_token': room_details['user_token']}}
        )
        
        # Initialize the interview manager
        interview_manager = InterviewManager(
            room_name=room_details['room_name'],
            interview_id=interview_id,
            questions=questions
        )
        
        # Start the interview
        interview_manager.start()
        
        # Store interview data in database (not the manager object)
        db.interviews.update_one(
            {'interview_id': interview_id},
            {'$set': {
                'room_name': room_details['room_name'],
                'questions': questions,
                'status': 'ready',
                'current_question_index': 0
            }}
        )
        
        return jsonify({
            'message': 'Resume processed successfully. Starting interview...',
            'interview_id': interview_id,
            'room_name': room_details['room_name'],
            'token': room_details['user_token'],
            'interview_url': f'/interview/{interview_id}',
            'processing_details': {
                'status': 'success',
                'time_taken': '2 seconds',
                'questions_generated': len(questions)
            }
        })
        
    except Exception as e:
        print(f"Error in upload_resume: {str(e)}")
        return jsonify({'message': f'Upload failed: {str(e)}'}), 500

# Interview instructions endpoint
@app.route('/interview-instructions', methods=['GET'])
@token_required
def get_interview_instructions(current_user):
    instructions = {
        'general_rules': [
            'The interview will be conducted via video call',
            'Please ensure you have a stable internet connection',
            'Find a quiet environment with minimal background noise',
            'Have your camera and microphone ready',
            'Answer only in English, answers in other languages will not be accepted',
            'Have a glass of water ready',
            'Dress professionally as you would for a real interview'
        ],
        'interview_format': [
            'The interview will last approximately 15 minutes',
            'It will include both technical and behavioral questions',
            'Questions will be based on your resume and general knowledge',
            'You will have time of 20 sec or else AI will move to next question',
            'The AI interviewer will provide real-time feedback'
        ],
        'technical_requirements': [
            'A computer with a working webcam and microphone',
            'Google Chrome or Firefox browser (latest version)',
            'Minimum internet speed of 5 Mbps',
            'A quiet, well-lit environment'
        ],
        'preparation_tips': [
            'Review your resume thoroughly',
            'Prepare examples of your past experiences',
            'Research common interview questions in your field',
            'Practice speaking clearly and concisely',
            'Prepare questions to ask the interviewer'
        ]
    }
    
    return jsonify(instructions)

@app.route('/interview-questions', methods=['GET'])
@token_required
def get_interview_questions(current_user):
    try:
        user = db.users.find_one({'_id': current_user['_id']})
        if not user or 'resume' not in user or 'questions_path' not in user['resume']:
            return jsonify({'message': 'No interview questions found'}), 404
        
        questions_path = user['resume']['questions_path']
        if not os.path.exists(questions_path):
            return jsonify({'message': 'Questions file not found'}), 404
        
        # Read questions as array (one question per line)
        with open(questions_path, 'r', encoding='utf-8') as f:
            questions = f.read().strip().split('\n')
        
        return jsonify(questions)  # Return simple array of questions
    except Exception as e:
        return jsonify({'message': f'Error retrieving questions: {str(e)}'}), 500


@app.route('/interview/<interview_id>', methods=['GET'])
def interview_room(interview_id):
    """Get interview room data."""
    try:
        # Find interview by interview_id instead of _id
        interview = db.interviews.find_one({'interview_id': interview_id})
        if not interview:
            print(f"Interview not found: {interview_id}")
            return jsonify({'message': 'Interview not found'}), 404
        
        # Get the candidate token
        token = interview.get('candidate_token')
        if not token:
            print(f"Token not found for interview: {interview_id}")
            return jsonify({'message': 'Interview token not found'}), 404
        
        # Get room name from interview or generate one
        room_name = interview.get('room_name')
        if not room_name:
            room_name = f"interview-{interview_id}"
            # Update the interview with the room name
            db.interviews.update_one(
                {'interview_id': interview_id},
                {'$set': {'room_name': room_name}}
            )
        
        # Get questions or use empty list
        questions = interview.get('questions', [])
        
        # Get bot name and avatar from config or use defaults
        bot_name = interview.get('bot_name', BOT_NAME)
        bot_avatar = interview.get('bot_avatar', BOT_AVATAR)
        
        print(f"Returning interview data for {interview_id}: room={room_name}, questions={len(questions)}")
        
        return jsonify({
            'token': token,
            'room_name': room_name,
            'questions': questions,
            'interview_id': interview_id,
            'bot_name': bot_name,
            'bot_avatar': bot_avatar,
            'status': interview.get('status', 'ready')
        })
        
    except Exception as e:
        print(f"Error accessing interview room: {str(e)}")
        # Log the full error for debugging
        import traceback
        print(traceback.format_exc())
        return jsonify({'message': f'Error accessing interview room: {str(e)}'}), 500

@app.route('/interview-status/<interview_id>', methods=['GET', 'POST'])
def interview_status(interview_id):
    """Get or update interview status."""
    try:
        if request.method == 'GET':
            # Find interview by interview_id
            interview = db.interviews.find_one({'interview_id': interview_id})
            if not interview:
                return jsonify({'message': 'Interview not found'}), 404
            
            return jsonify({
                'status': interview['status'],
                'current_question_index': interview.get('current_question_index', 0),
                'questions': interview['questions'],
                'room_name': interview['room_name']
            })
            
        elif request.method == 'POST':
            data = request.get_json()
            status = data.get('status')
            recording_url = data.get('recording_url')
            question_index = data.get('question_index')
            response_text = data.get('response_text')
            
            if not all([status, recording_url, question_index is not None]):
                return jsonify({'message': 'Missing required fields'}), 400
            
            update_data = {
                'status': status,
                '$push': {
                    'recordings': {
                        'question_index': question_index,
                        'recording_url': recording_url,
                        'response_text': response_text,
                        'timestamp': datetime.now(timezone.utc)
                    }
                }
            }
            
            if status == 'completed':
                update_data['$set'] = {'completed_at': datetime.now(timezone.utc)}
            
            # Update using interview_id
            result = db.interviews.update_one(
                {'interview_id': interview_id},
                update_data
            )
            
            if result.modified_count == 0:
                return jsonify({'message': 'Interview not found or no changes made'}), 404
            
            return jsonify({'message': 'Interview status updated successfully'})
            
    except Exception as e:
        print(f"Error handling interview status: {str(e)}")
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/interview-recordings/<interview_id>', methods=['GET'])
@token_required
def get_interview_recordings(current_user, interview_id):
    """Get recordings and responses for a specific interview."""
    try:
        interview = db.interviews.find_one({
            '_id': ObjectId(interview_id),
            'user_id': current_user['_id']
        })
        
        if not interview:
            return jsonify({'message': 'Interview not found'}), 404
        
        # Format the response data
        recordings = []
        for response in interview.get('recordings', []):
            question = interview['questions'][response['question_index']]
            recordings.append({
                'question': question,
                'response': response.get('response_text', ''),
                'recording_url': response.get('recording_url'),
                'timestamp': response['timestamp'].isoformat()
            })
        
        return jsonify({
            'interview_id': str(interview['_id']),
            'status': interview['status'],
            'scheduled_time': interview['scheduled_time'].isoformat(),
            'recordings': recordings
        })
        
    except Exception as e:
        print(f"Error retrieving interview recordings: {str(e)}")
        return jsonify({'message': f'Error retrieving recordings: {str(e)}'}), 500

@app.route('/interview/<interview_id>/token', methods=['POST'])
def get_token(interview_id):
    """Generate a token for the interview room."""
    try:
        # Find interview by interview_id
        interview = db.interviews.find_one({'interview_id': interview_id})
        if not interview:
            return jsonify({'message': 'Interview not found'}), 404
            
        # Create an access token
        token = AccessToken(
            TWILIO_ACCOUNT_SID,
            TWILIO_API_KEY,
            TWILIO_API_SECRET,
            identity=f"tts_{interview_id}"
        )
        
        # Create a Video grant and add it to the token
        video_grant = VideoGrant(room=interview['room_name'])
        token.add_grant(video_grant)
        
        # Generate the token
        token = token.to_jwt().decode()
        
        return jsonify({
            'token': token,
            'room_name': interview['room_name'],
            'current_question_index': interview.get('current_question_index', 0),
            'questions': interview['questions']
        })
        
    except Exception as e:
        print(f"Error generating token: {str(e)}")
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/interview/<interview_id>/record-response', methods=['POST'])
def record_response(interview_id):
    """Record and transcribe candidate response."""
    try:
        # Find interview by interview_id
        interview = db.interviews.find_one({'interview_id': interview_id})
        if not interview:
            return jsonify({'message': 'Interview not found'}), 404
        
        data = request.get_json()
        question_index = data.get('question_index', 0)
        audio_blob = data.get('audio_blob')  # Base64 encoded audio data
        
        if not audio_blob:
            return jsonify({'message': 'No audio data provided'}), 400
        
        print(f"Processing audio for question {question_index} in interview {interview_id}")
        
        # Save audio file temporarily with proper extension
        import base64
        try:
            # Handle different audio formats
            if 'data:audio/webm' in audio_blob:
                audio_data = base64.b64decode(audio_blob.split(',')[1])
                temp_audio_path = os.path.join(UPLOAD_FOLDER, f"temp_audio_{interview_id}_{question_index}.webm")
            elif 'data:audio/wav' in audio_blob:
                audio_data = base64.b64decode(audio_blob.split(',')[1])
                temp_audio_path = os.path.join(UPLOAD_FOLDER, f"temp_audio_{interview_id}_{question_index}.wav")
            else:
                # Default to webm
                audio_data = base64.b64decode(audio_blob.split(',')[1])
                temp_audio_path = os.path.join(UPLOAD_FOLDER, f"temp_audio_{interview_id}_{question_index}.webm")
            
            print(f"Saving audio to: {temp_audio_path}")
            print(f"Audio data size: {len(audio_data)} bytes")
            
            with open(temp_audio_path, 'wb') as f:
                f.write(audio_data)
            
            # Verify file was written
            if not os.path.exists(temp_audio_path) or os.path.getsize(temp_audio_path) == 0:
                return jsonify({'message': 'Failed to save audio file'}), 500
            
            print(f"Audio file saved successfully, size: {os.path.getsize(temp_audio_path)} bytes")
            
        except Exception as audio_error:
            print(f"Error saving audio: {audio_error}")
            return jsonify({'message': f'Error saving audio: {str(audio_error)}'}), 500
        
        # Transcribe audio
        print("Starting transcription...")
        transcription = transcribe_audio(temp_audio_path)
        print(f"Transcription result: {transcription}")
        
        # Clean up temporary file
        try:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
                print("Temporary audio file cleaned up")
        except Exception as cleanup_error:
            print(f"Error cleaning up audio file: {cleanup_error}")
        
        if not transcription:
            transcription = "No speech detected in audio recording"
        
        # Store transcription in database
        response_data = {
            'question_index': question_index,
            'question': interview['questions'][question_index] if question_index < len(interview.get('questions', [])) else 'Unknown question',
            'transcription': transcription,
            'timestamp': datetime.now(timezone.utc),
            'audio_processed': True
        }
        
        print(f"Storing response data: {response_data}")
        
        # Update interview with response
        result = db.interviews.update_one(
            {'interview_id': interview_id},
            {'$push': {'responses': response_data}}
        )
        
        print(f"Database update result: modified_count={result.modified_count}")
        
        return jsonify({
            'message': 'Response recorded and transcribed successfully',
            'transcription': transcription,
            'question_index': question_index,
            'audio_size': len(audio_data)
        })
        
    except Exception as e:
        print(f"Error recording response: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/interview/<interview_id>/complete', methods=['POST'])
def complete_interview(interview_id):
    """Complete interview and generate report."""
    try:
        # Find interview by interview_id
        interview = db.interviews.find_one({'interview_id': interview_id})
        if not interview:
            return jsonify({'message': 'Interview not found'}), 404
        
        # Get user details
        user = db.users.find_one({'_id': interview['user_id']})
        candidate_name = user.get('name', 'Candidate') if user else 'Candidate'
        candidate_email = user.get('email', 'unknown@email.com') if user else 'unknown@email.com'
        
        # Check if interview has responses, if not create a basic structure
        responses = interview.get('responses', [])
        if not responses:
            # Create dummy responses if none exist
            questions = interview.get('questions', [])
            responses = []
            for i, question in enumerate(questions):
                responses.append({
                    'question_index': i,
                    'question': question,
                    'transcription': 'No response recorded',
                    'timestamp': datetime.now(timezone.utc)
                })
            
            # Update interview with dummy responses
            db.interviews.update_one(
                {'interview_id': interview_id},
                {'$set': {'responses': responses}}
            )
            interview['responses'] = responses
        
        # Generate report
        report_content = generate_interview_report(interview)
        if not report_content:
            # Create a basic report if AI generation fails
            report_content = f"""
INTERVIEW ASSESSMENT REPORT

CANDIDATE: {candidate_name}
EMAIL: {candidate_email}
DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

INTERVIEW SUMMARY:
The candidate participated in an AI-conducted interview session. Due to technical limitations, 
detailed analysis could not be completed automatically.

QUESTIONS ASKED:
{chr(10).join([f"{i+1}. {q}" for i, q in enumerate(interview.get('questions', []))])}

RESPONSES:
{chr(10).join([f"Q{r.get('question_index', 0)+1}: {r.get('transcription', 'No response')}" for r in responses])}

RECOMMENDATION:
Manual review recommended for final assessment.

SCORE: Pending manual review
"""
        
        # Create PDF report
        pdf_buffer = create_pdf_report(report_content, candidate_name)
        
        # Send email with report
        email_sent = False
        if pdf_buffer:
            email_sent = send_report_email(pdf_buffer, candidate_name)
        
        # Update interview status
        db.interviews.update_one(
            {'interview_id': interview_id},
            {'$set': {
                'status': 'completed',
                'completed_at': datetime.now(timezone.utc),
                'report_generated': True,
                'report_sent': email_sent,
                'report_content': report_content
            }}
        )
        
        return jsonify({
            'message': 'Interview completed successfully',
            'report_generated': True,
            'email_sent': email_sent,
            'candidate_name': candidate_name,
            'total_questions': len(interview.get('questions', [])),
            'total_responses': len(responses),
            'report_preview': report_content[:300] + '...' if len(report_content) > 300 else report_content
        })
        
    except Exception as e:
        print(f"Error completing interview: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'message': f'Error completing interview: {str(e)}'}), 500

@app.route('/interview/<interview_id>/next-question', methods=['POST'])
def next_question(interview_id):
    """Move to the next question in the interview."""
    try:
        # Find interview by interview_id
        interview = db.interviews.find_one({'interview_id': interview_id})
        if not interview:
            return jsonify({'message': 'Interview not found'}), 404
            
        # Create a new manager instance from interview data
        manager = InterviewManager.from_interview(interview)
        manager.current_question_index = interview.get('current_question_index', 0)
        
        # Move to next question
        manager.current_question_index += 1
        if manager.current_question_index >= len(manager.questions):
            manager.update_interview_status('completed')
            return jsonify({
                'message': 'Interview completed',
                'has_more_questions': False,
                'current_question_index': manager.current_question_index
            })
            
        # Update status
        manager.update_interview_status('in_progress', {
            'current_question_index': manager.current_question_index
        })
        
        return jsonify({
            'message': 'Moved to next question',
            'has_more_questions': True,
            'current_question_index': manager.current_question_index,
            'question': manager.questions[manager.current_question_index]
        })
        
    except Exception as e:
        print(f"Error moving to next question: {str(e)}")
        return jsonify({'message': f'Error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
