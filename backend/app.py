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
import whisper
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
    """Parse resume using OpenAI to extract key information."""
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """Extract key information from the resume. 
                Focus on:
                1. Technical skills and programming languages
                2. Work experience and projects
                3. Education and certifications
                4. Notable achievements
                
                Format the response as a structured summary that can be used to generate relevant interview questions."""},
                {"role": "user", "content": f"Parse this resume and extract key information:\n\n{resume_text}"}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        parsed_data = response.choices[0].message.content.strip()
        print("Successfully parsed resume with OpenAI")
        return parsed_data
        
    except Exception as e:
        print(f"Error parsing resume with OpenAI: {str(e)}")
        return None

def generate_interview_questions(resume_text):
    """Generate interview questions based on resume content using OpenAI."""
    try:
        # Parse resume with OpenAI
        resume_data = parse_resume_with_openai(resume_text)
        if not resume_data:
            raise Exception("Failed to parse resume")
        
        # Generate interview questions based on parsed resume data
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """You are an expert technical interviewer. 
                Based on the candidate's resume information, generate 2 relevant technical interview questions.
                The questions should be specific to their experience and skills.
                Return ONLY an array of 2 questions, nothing else."""},
                {"role": "user", "content": f"Generate 2 technical interview questions based on this resume information:\n\n{resume_data}"}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        # Extract questions from response
        questions = response.choices[0].message.content.strip().split('\n')
        # Clean up questions (remove numbers, extra spaces, etc.)
        questions = [q.strip().lstrip('1234567890.- ') for q in questions if q.strip()]
        
        # Ensure we have exactly 2 questions
        if len(questions) > 2:
            questions = questions[:2]
        elif len(questions) < 2:
            # Add a fallback question if we don't have enough
            questions.append("Tell me about your most challenging technical project and how you overcame the obstacles.")
        
        print(f"Generated {len(questions)} questions from resume")
        return questions
        
    except Exception as e:
        print(f"Error generating interview questions: {str(e)}")
        # Return fallback questions if there's an error
        return [
            "Tell me about your most challenging technical project and how you overcame the obstacles.",
            "What technical skills are you most proud of and why?"
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
    """Transcribe audio file to text using OpenAI Whisper."""
    try:
        print(f"Starting Whisper transcription for: {audio_file_path}")
        
        # Verify file exists before processing
        if not os.path.exists(audio_file_path):
            print(f"ERROR: Audio file does not exist: {audio_file_path}")
            return f"Error: Audio file not found at {audio_file_path}"
            
        # Get absolute path to ensure no path resolution issues
        audio_file_path = os.path.abspath(audio_file_path)
        print(f"Using absolute path: {audio_file_path}")
        
        # File size verification
        file_size = os.path.getsize(audio_file_path)
        print(f"Audio file size: {file_size} bytes")
        if file_size == 0:
            return "Error: Audio file is empty (0 bytes)"
        
        # Convert audio to wav format using FFmpeg directly
        wav_path = os.path.join(os.path.dirname(audio_file_path), 
                              f"whisper_temp_{uuid.uuid4().hex}.wav")
        
        print(f"Converting audio to WAV format at: {wav_path}")
        
        # Use FFmpeg to convert the audio with explicit path
        ffmpeg_path = os.path.join(FFMPEG_PATH, "ffmpeg.exe")
        ffmpeg_cmd = [
            ffmpeg_path,
            "-i", audio_file_path,
            "-ar", "16000",  # Sample rate
            "-ac", "1",      # Mono channel
            "-y",            # Overwrite if exists
            wav_path
        ]
        
        print(f"Running FFmpeg command: {' '.join(ffmpeg_cmd)}")
        import subprocess
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        
        # Verify the WAV file was created
        if not os.path.exists(wav_path):
            print(f"ERROR: FFmpeg failed to create WAV file at {wav_path}")
            return "Error: Failed to convert audio format"
            
        print(f"WAV file created successfully: {wav_path}")
        print(f"WAV file size: {os.path.getsize(wav_path)} bytes")
        
        # Load Whisper model
        print("Loading Whisper model...")
        model = whisper.load_model("base")
        
        # Transcribe using Whisper
        print(f"Transcribing audio...")
        result = model.transcribe(wav_path)
        transcription = result["text"].strip()
        
        print(f"=== WHISPER TRANSCRIPTION RESULT ===")
        print(f"Original audio file: {audio_file_path}")
        print(f"Transcribed text: '{transcription}'")
        print(f"=====================================")
        
        if not transcription:
            transcription = "No speech detected in audio recording"
            print("Warning: Empty transcription result")
        
        return transcription
        
    except FileNotFoundError as e:
        error_msg = f"Audio file not found error: {str(e)}"
        print(error_msg)
        return f"Error during Whisper transcription: {error_msg}"
    except subprocess.CalledProcessError as e:
        error_msg = f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}"
        print(error_msg)
        return f"Error during audio conversion: {error_msg}"
    except Exception as e:
        error_msg = f"Error transcribing audio: {str(e)}"
        print(error_msg)
        import traceback
        print(traceback.format_exc())
        return f"Error during Whisper transcription: {str(e)}"
    finally:
        # Clean up temporary wav file
        try:
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.remove(wav_path)
                print(f"Cleaned up temporary file: {wav_path}")
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
            response = next((r for r in responses if r.get('question_index') == i), None)
            
            answer = response.get('transcription', 'No response recorded') if response else 'No response recorded'
            # Skip error messages in the analysis
            if answer.startswith('Error during Whisper transcription'):
                answer = 'No valid response recorded'
                
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
            if answer.startswith('Error during Whisper transcription'):
                answer = 'No valid response recorded'
                
            fallback_report += f"\nQ{i+1}: {question}\nA{i+1}: {answer[:100]}{'...' if len(answer) > 100 else ''}\n"
        
        fallback_report += "\n\nRECOMMENDATION: Manual review required\nSCORE: Pending detailed analysis"
        
        return fallback_report

def create_pdf_report(report_content, candidate_name="Candidate", status="Pending Review", score="N/A"):
    """Create PDF report from text content."""
    try:
        buffer = io.BytesIO()
        
        # Initialize PDF document
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            title=f"Interview Report - {candidate_name}",
            author="Lsoys Apps & Games - AI Interviewer System",
            subject="Interview Assessment"
        )
        
        # Extract score from report content if not provided
        if score == "N/A" and "SCORE:" in report_content:
            # Try to find the score in the report
            score_line = [line for line in report_content.split('\n') if "SCORE:" in line]
            if score_line:
                try:
                    score = score_line[0].split("SCORE:")[1].strip()
                except:
                    score = "N/A"
        
        # Get style sheets and define custom styles
        styles = getSampleStyleSheet()
        
        # Company header style
        company_style = ParagraphStyle(
            'CompanyHeader',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=1,  # Center alignment
            textColor='#1A237E',  # Dark blue
            fontName='Helvetica-Bold',
            spaceAfter=6
        )
        
        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=5,
            alignment=1,  # Center alignment
            textColor='#1A237E'  # Dark blue
        )
        
        # Subtitle style (candidate name)
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=14,
            alignment=1,  # Center
            spaceAfter=10
        )
        
        # Status box style
        status_style = ParagraphStyle(
            'StatusStyle',
            parent=styles['Heading2'],
            fontSize=12,
            alignment=1,  # Center
            textColor='white',
            backColor=get_status_color(status),
            borderWidth=1,
            borderColor='#333333',
            borderPadding=5,
            borderRadius=4,
            spaceAfter=10
        )
        
        # Score style
        score_style = ParagraphStyle(
            'ScoreStyle',
            parent=styles['Heading2'],
            fontSize=14,
            alignment=1,  # Center
            textColor='#333333',
            spaceAfter=5
        )
        
        # Date style
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=1,  # Center
            textColor='#666666',
            spaceAfter=15
        )
        
        # Section heading style
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=12,
            spaceAfter=8,
            textColor='#283593',  # Indigo
            borderWidth=0,
            borderColor='#C5CAE9',
            borderPadding=5,
            borderRadius=2
        )
        
        # Subheading style
        subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            textColor='#303F9F'  # Darker indigo
        )
        
        # Body text style
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            leading=14  # Line spacing
        )
        
        # Question style
        question_style = ParagraphStyle(
            'QuestionStyle',
            parent=styles['Normal'],
            fontSize=11,
            fontName='Helvetica-Bold',
            spaceAfter=2,
            textColor='#1A237E',
            leftIndent=10
        )
        
        # Answer style
        answer_style = ParagraphStyle(
            'AnswerStyle',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=12,
            leftIndent=20,
            leading=14  # Line spacing
        )
        
        # Footer style
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=8,
            alignment=1,  # Center
            textColor='#666666'
        )
        
        # Build PDF content
        story = []
        
        # Add company header
        story.append(Paragraph("LSOYS APPS & GAMES", company_style))
        
        # Add title
        story.append(Paragraph("INTERVIEW ASSESSMENT REPORT", title_style))
        
        # Add candidate name
        story.append(Paragraph(f"Candidate: {candidate_name}", subtitle_style))
        
        # Add status box
        story.append(Paragraph(f"Status: {status}", status_style))
        
        # Add score prominently
        story.append(Paragraph(f"SCORE: {score}", score_style))
        
        # Add date and time
        current_time = datetime.now().strftime("%B %d, %Y at %H:%M")
        story.append(Paragraph(f"Generated on: {current_time}", date_style))
        
        # Add horizontal line
        story.append(Spacer(1, 10))
        
        # Split report into sections and format
        sections = report_content.split('\n')
        current_section = None
        in_qa_section = False
        skip_score_section = False  # Skip the original score section since we've moved it to the top
        
        for section in sections:
            if not section.strip():
                story.append(Spacer(1, 6))
                continue
            
            # Skip the original score section
            if "SCORE:" in section:
                skip_score_section = True
                continue
                
            if skip_score_section and section.strip() and not section.strip().isupper():
                skip_score_section = False
                
            if skip_score_section:
                continue
                
            if "INTERVIEW QUESTIONS & ANSWERS" in section:
                in_qa_section = True
                story.append(Spacer(1, 10))
                story.append(Paragraph(section.strip(), heading_style))
                story.append(Spacer(1, 10))
                continue
            
            if in_qa_section:
                if section.strip().startswith("Question"):
                    story.append(Paragraph(section.strip(), question_style))
                elif section.strip().startswith("Response:"):
                    story.append(Paragraph(section.strip(), answer_style))
            elif section.strip().isupper() and len(section.strip()) < 50:
                # This is a section heading
                current_section = section.strip()
                story.append(Spacer(1, 10))
                story.append(Paragraph(current_section, heading_style))
                story.append(Spacer(1, 5))
            else:
                story.append(Paragraph(section.strip(), body_style))
        
        # Add footer with attribution and website link
        story.append(Spacer(1, 20))

        story.append(Spacer(1, 10))
        story.append(Paragraph("Generated by AI Interviewer | www.lsoysappsandgames.com/ai-interviewer", footer_style))
        
        # Build the document
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Error creating PDF: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

# Helper function to determine status color
def get_status_color(status):
    """Return color code based on candidate status."""
    status = status.lower()
    if "selected" in status:
        return "#4CAF50"  # Green
    elif "next round" in status:
        return "#2196F3"  # Blue
    elif "rejected" in status:
        return "#F44336"  # Red
    elif "not good" in status:
        return "#FF9800"  # Orange
    elif "good in another role" in status:
        return "#9C27B0"  # Purple
    else:
        return "#757575"  # Grey for pending/unknown

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
        # Find interview by interview_id
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
    temp_audio_path = None
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
        
        # Create unique filename with timestamp to avoid overwriting
        timestamp = int(time.time())
        temp_filename = f"audio_{interview_id}_{question_index}_{timestamp}"
        
        # Save audio file temporarily with proper extension
        import base64
        try:
            # Handle different audio formats
            if 'data:audio/webm' in audio_blob:
                audio_data = base64.b64decode(audio_blob.split(',')[1])
                temp_audio_path = os.path.join(UPLOAD_FOLDER, f"{temp_filename}.webm")
            elif 'data:audio/wav' in audio_blob:
                audio_data = base64.b64decode(audio_blob.split(',')[1])
                temp_audio_path = os.path.join(UPLOAD_FOLDER, f"{temp_filename}.wav")
            else:
                # Default to webm
                audio_data = base64.b64decode(audio_blob.split(',')[1])
                temp_audio_path = os.path.join(UPLOAD_FOLDER, f"{temp_filename}.webm")
            
            # Ensure the upload folder exists
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
            print(f"Saving audio to: {temp_audio_path}")
            print(f"Audio data size: {len(audio_data)} bytes")
            
            with open(temp_audio_path, 'wb') as f:
                f.write(audio_data)
            
            # Verify file was written
            if not os.path.exists(temp_audio_path):
                return jsonify({'message': 'Failed to save audio file - file not found'}), 500
                
            if os.path.getsize(temp_audio_path) == 0:
                return jsonify({'message': 'Failed to save audio file - file size is 0 bytes'}), 500
            
            print(f"Audio file saved successfully at {temp_audio_path}")
            print(f"File size: {os.path.getsize(temp_audio_path)} bytes")
            print(f"File exists check: {os.path.exists(temp_audio_path)}")
            
        except Exception as audio_error:
            print(f"Error saving audio: {audio_error}")
            return jsonify({'message': f'Error saving audio: {str(audio_error)}'}), 500
        
        # Transcribe audio
        print("Starting transcription...")
        transcription = transcribe_audio(temp_audio_path)
        print(f"Transcription result: {transcription}")
        
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
        
        print(f"=== STORING RESPONSE DATA ===")
        print(f"Interview ID: {interview_id}")
        print(f"Question Index: {question_index}")
        print(f"Question: {response_data['question']}")
        print(f"Transcription: '{transcription}'")
        print(f"Audio Size: {len(audio_data)} bytes")
        print("============================")
        
        # Update interview with response
        result = db.interviews.update_one(
            {'interview_id': interview_id},
            {'$push': {'responses': response_data}}
        )
        
        print(f"Database update result: modified_count={result.modified_count}")
        
        # Verify the data was stored
        updated_interview = db.interviews.find_one({'interview_id': interview_id})
        responses_count = len(updated_interview.get('responses', []))
        print(f"Total responses now stored: {responses_count}")
        
        return jsonify({
            'message': 'Response recorded and transcribed successfully',
            'transcription': transcription,
            'question_index': question_index,
            'audio_size': len(audio_data),
            'total_responses': responses_count
        })
        
    except Exception as e:
        print(f"Error recording response: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'message': f'Error: {str(e)}'}), 500
    finally:
        # Clean up temporary file ONLY after transcription is complete
        try:
            if temp_audio_path and os.path.exists(temp_audio_path):
                # Keep the file for debugging if there was an error in the transcription
                if "Error during Whisper transcription" not in str(transcription):
                    os.remove(temp_audio_path)
                    print(f"Cleaned up audio file: {temp_audio_path}")
                else:
                    print(f"Keeping audio file for debugging: {temp_audio_path}")
        except Exception as cleanup_error:
            print(f"Error cleaning up audio file: {cleanup_error}")

@app.route('/interview/<interview_id>/complete', methods=['POST'])
def complete_interview(interview_id):
    """Complete interview and generate report."""
    try:
        print(f"=== COMPLETING INTERVIEW {interview_id} ===")
        
        # Find interview by interview_id
        interview = db.interviews.find_one({'interview_id': interview_id})
        if not interview:
            print(f"Interview not found: {interview_id}")
            return jsonify({'message': 'Interview not found'}), 404
        
        # Enhanced duplicate check: Check completion status and report_sent flag
        # Use an atomic update with a unique completion ID to prevent race conditions
        completion_id = str(uuid.uuid4())
        
        # Use findAndModify (find_one_and_update) to atomically check and update
        # Only proceed if the interview is not already completed or email not sent
        result = db.interviews.find_one_and_update(
            {
                'interview_id': interview_id, 
                '$or': [
                    {'status': {'$ne': 'completed'}},
                    {'report_sent': {'$ne': True}}
                ]
            },
            {'$set': {
                'completion_process_id': completion_id,
                'completion_started_at': datetime.now(timezone.utc)
            }},
            return_document=False
        )
        
        # If no document was updated, another process is already completing it
        if not result:
            print(f"Interview {interview_id} already being completed or email already sent")
            # Return the existing report content if available
            existing_interview = db.interviews.find_one({'interview_id': interview_id})
            return jsonify({
                'message': 'Interview already completed or being processed',
                'report_generated': True,
                'email_sent': existing_interview.get('report_sent', False),
                'candidate_name': existing_interview.get('candidate_name', 'Candidate'),
                'report_content': existing_interview.get('report_content', 'Report not available')
            })
        
        # Get user details
        user = db.users.find_one({'_id': interview['user_id']})
        candidate_name = user.get('name', 'Candidate') if user else 'Candidate'
        candidate_email = user.get('email', 'unknown@email.com') if user else 'unknown@email.com'
        
        print(f"Processing completion for candidate: {candidate_name} ({candidate_email})")
        
        # Check if interview has responses, if not create a basic structure
        responses = interview.get('responses', [])
        print(f"Found {len(responses)} responses")
        
        # Print all responses for verification
        print("=== CANDIDATE RESPONSES ===")
        for i, response in enumerate(responses):
            print(f"Response {i+1}:")
            print(f"  Question Index: {response.get('question_index', 'N/A')}")
            print(f"  Question: {response.get('question', 'N/A')}")
            print(f"  Transcription: '{response.get('transcription', 'No response')}'")
            print(f"  Timestamp: {response.get('timestamp', 'N/A')}")
            print("---")
        
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
            print("Created dummy responses for empty interview")
        
        # Create Q&A section for the report
        qa_section = "INTERVIEW QUESTIONS & ANSWERS:\n\n"
        questions = interview.get('questions', [])
        for i, question in enumerate(questions):
            # Find corresponding response
            response = None
            for r in responses:
                if r.get('question_index') == i:
                    response = r
                    break
            
            answer = response.get('transcription', 'No response recorded') if response else 'No response recorded'
            qa_section += f"Question {i+1}: {question}\n"
            qa_section += f"Response: {answer}\n\n"
        
        # Generate report
        print("Generating interview report...")
        report_content = generate_interview_report(interview)
        
        print("=== GENERATED REPORT PREVIEW ===")
        print(report_content[:500] + "..." if len(report_content) > 500 else report_content)
        print("===============================")
        
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

{qa_section}

RECOMMENDATION:
Manual review recommended for final assessment.

SCORE: Pending manual review
"""
            print("Using fallback report due to AI generation failure")
        else:
            # Append the Q&A section to the AI-generated report
            report_content += f"\n\n{qa_section}"
        
        # Create PDF report
        print("Creating PDF report...")
        pdf_buffer = create_pdf_report(report_content, candidate_name)
        
        # Check if report already sent to prevent duplicate emails
        report_already_sent = interview.get('report_sent', False)
        
        # Send email with report (only if not already sent)
        email_sent = False
        if pdf_buffer and not report_already_sent:
            print("Sending email with report...")
            email_sent = send_report_email(pdf_buffer, candidate_name, recipient_email="piyushkrishna11@gmail.com")
            print(f"Email sent: {email_sent}")
        elif report_already_sent:
            print("Skipping email send - report was already sent previously")
            email_sent = True
        else:
            print("Skipping email (PDF creation failed)")
        
        # Update interview status with completion ID to ensure this process is still the active one
        update_result = db.interviews.update_one(
            {
                'interview_id': interview_id,
                'completion_process_id': completion_id  # Ensure we're still the active process
            },
            {'$set': {
                'status': 'completed',
                'completed_at': datetime.now(timezone.utc),
                'report_generated': True,
                'report_sent': email_sent,
                'report_content': report_content,
                'candidate_name': candidate_name
            }}
        )
        
        # Check if our update was successful
        if update_result.modified_count == 0:
            print(f"Interview completion collision detected for {interview_id}")
            # Retrieve the latest interview data to return correct report
            latest_interview = db.interviews.find_one({'interview_id': interview_id})
            return jsonify({
                'message': 'Interview was completed by another process',
                'report_generated': True,
                'email_sent': latest_interview.get('report_sent', False),
                'report_content': latest_interview.get('report_content', 'Report not available')
            })
        
        print(f"Interview {interview_id} completion processed successfully")
        
        return jsonify({
            'message': 'Interview completed successfully',
            'report_generated': True,
            'email_sent': email_sent,
            'candidate_name': candidate_name,
            'report_content': report_content  # Return the report content in the response
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
        
        # Get question played status from request
        data = request.get_json() or {}
        is_new_question = data.get('is_new_question', True)
        
        # Create a new manager instance from interview data
        manager = InterviewManager.from_interview(interview)
        manager.current_question_index = interview.get('current_question_index', 0)
        
        # If this is a new question, increment the index
        if is_new_question:
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
            'current_question_index': manager.current_question_index,
            'question_played': not is_new_question  # Track if question has been played
        })
        
        return jsonify({
            'message': 'Moved to next question' if is_new_question else 'Current question refreshed',
            'has_more_questions': True,
            'current_question_index': manager.current_question_index,
            'question': manager.questions[manager.current_question_index],
            'question_played': not is_new_question  # Indicate if question has been played
        })
        
    except Exception as e:
        print(f"Error moving to next question: {str(e)}")
        return jsonify({'message': f'Error: {str(e)}'}), 500

class InterviewManager:
    """Manages the interview process and state."""
    
    def __init__(self, room_name, interview_id, questions):
        self.room_name = room_name
        self.interview_id = interview_id
        self.questions = questions
        self.current_question_index = 0
        self.status = 'ready'
    
    @classmethod
    def from_interview(cls, interview):
        """Create an InterviewManager instance from an interview document."""
        return cls(
            room_name=interview.get('room_name', f"interview-{interview['interview_id']}"),
            interview_id=interview['interview_id'],
            questions=interview.get('questions', [])
        )
    
    def start(self):
        """Start the interview."""
        self.status = 'in_progress'
        self.update_interview_status('in_progress')
        print(f"Started interview {self.interview_id} with {len(self.questions)} questions")
    
    def update_interview_status(self, status, additional_data=None):
        """Update the interview status in the database."""
        try:
            update_data = {'status': status}
            
            # Add any additional data to the update
            if additional_data:
                for key, value in additional_data.items():
                    update_data[key] = value
            
            # Update the interview document
            result = db.interviews.update_one(
                {'interview_id': self.interview_id},
                {'$set': update_data}
            )
            
            self.status = status
            print(f"Updated interview {self.interview_id} status to {status}, modified: {result.modified_count}")
            
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating interview status: {str(e)}")
            return False
def create_interview_room(interview_id, user_id):
    """Create a Twilio video room for an interview and generate token."""
    try:
        # Generate a unique room name
        room_name = f"interview-{interview_id}"
        
        # Check if room already exists
        try:
            # Try to fetch the room (will throw an exception if it doesn't exist)
            room = twilio_client.video.v1.rooms(room_name).fetch()
            print(f"Room {room_name} already exists with SID: {room.sid}")
        except TwilioRestException as e:
            if e.status == 404:
                # Room doesn't exist, create it
                room = twilio_client.video.v1.rooms.create(
                    unique_name=room_name,
                    type='group',
                    record_participants_on_connect=False,
                    status_callback=f"https://yourserver.com/room-callback/{interview_id}",
                    max_participants=3  # Candidate, interviewer, and supervisor
                )
                print(f"Created new room: {room_name} with SID: {room.sid}")
            else:
                # Some other error occurred
                raise e
        
        # Generate token for the user
        token = AccessToken(
            TWILIO_ACCOUNT_SID, 
            TWILIO_API_KEY, 
            TWILIO_API_SECRET, 
            identity=f"user-{user_id}"
        )
        
        # Add video grant to the token
        video_grant = VideoGrant(room=room_name)
        token.add_grant(video_grant)
        
        # Generate JWT token
        jwt_token = token.to_jwt()
        
        if isinstance(jwt_token, bytes):
            jwt_token = jwt_token.decode()
        
        return {
            'room_name': room_name,
            'user_token': jwt_token
        }
        
    except Exception as e:
        print(f"Error creating interview room: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise e

# Set FFmpeg path
FFMPEG_PATH = r"C:\Users\HP\Downloads\ffmpeg-2025-06-11-git-f019dd69f0-essentials_build\ffmpeg-2025-06-11-git-f019dd69f0-essentials_build\bin"
os.environ["PATH"] = FFMPEG_PATH + os.pathsep + os.environ["PATH"]

# Also set the paths directly for pydub
AudioSegment.converter = os.path.join(FFMPEG_PATH, "ffmpeg.exe")
AudioSegment.ffmpeg = os.path.join(FFMPEG_PATH, "ffmpeg.exe")
AudioSegment.ffprobe = os.path.join(FFMPEG_PATH, "ffprobe.exe")

print(f"FFmpeg path set to: {FFMPEG_PATH}")

@app.route('/test-ffmpeg', methods=['GET'])
def test_ffmpeg():
    """Test if FFmpeg is properly configured."""
    try:
        # Check if ffmpeg exists
        ffmpeg_path = os.path.join(FFMPEG_PATH, "ffmpeg.exe")
        ffmpeg_exists = os.path.exists(ffmpeg_path)
        
        # Run ffmpeg -version command
        import subprocess
        result = subprocess.run(
            [ffmpeg_path, "-version"], 
            capture_output=True, 
            text=True
        )
        
        return jsonify({
            'ffmpeg_exists': ffmpeg_exists,
            'ffmpeg_path': ffmpeg_path,
            'version_output': result.stdout,
            'status': 'FFmpeg is properly configured' if result.returncode == 0 else 'FFmpeg test failed',
            'return_code': result.returncode
        })
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc(),
            'status': 'FFmpeg test failed'
        }), 500

def send_report_email(report_pdf, candidate_name="Candidate", recipient_email="piyushkrishna11@gmail.com"):
    """Send interview report via email."""
    try:
        print(f"Preparing to send email to {recipient_email} for candidate {candidate_name}")
        
        # Create a unique email ID based on candidate name and timestamp
        email_id = f"{candidate_name.lower().replace(' ', '_')}_{int(time.time())}"
        
        # Check if we've already sent this email recently (within last hour)
        # Use MongoDB to track sent emails
        existing_email = db.sent_emails.find_one({
            'candidate_name': candidate_name,
            'recipient': recipient_email,
            'sent_at': {'$gt': datetime.now(timezone.utc) - timedelta(hours=1)}
        })
        
        if existing_email:
            print(f"Email already sent to {recipient_email} for {candidate_name} within the last hour")
            return True  # Return success since we're preventing a duplicate
        
        print(f"Creating email with ID: {email_id}")
        
        msg = MIMEMultipart()
        msg['Subject'] = f"Interview Assessment Report - {candidate_name}"
        msg['From'] = 'piyushkrishna11@gmail.com'
        msg['To'] = recipient_email
        msg['Date'] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
        msg['Message-ID'] = f"<{email_id}@assessai.com>"
        
        # Email body with interview details
        body = f"""
Dear Hiring Manager,

Please find attached the comprehensive interview assessment report for {candidate_name}.

The report includes:
- Candidate overview
- Strengths and areas for improvement
- Technical and communication skills assessment
- Complete transcript of questions and answers
- Overall recommendation and scoring

This report was generated automatically by AssessAI based on the candidate's interview responses.

Best regards,
Lsoys Apps & Games
AI Interviewer System
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF report
        if report_pdf:
            print(f"Attaching PDF report for {candidate_name}")
            part = MIMEApplication(report_pdf.getvalue(), Name=f"{candidate_name}_Interview_Report.pdf")
            part['Content-Disposition'] = f'attachment; filename="{candidate_name}_Interview_Report.pdf"'
            msg.attach(part)
        else:
            print("Warning: No PDF report to attach")
            
        # Get Gmail password from environment
        gmail_password = os.getenv("GMAIL_PASS")
        if not gmail_password:
            print("Error: GMAIL_PASS environment variable not set")
            return False
        
        print(f"Connecting to Gmail SMTP server...")
        
        # Send email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login('piyushkrishna11@gmail.com', gmail_password)
            smtp.send_message(msg)
            
            # Record the sent email in database
            db.sent_emails.insert_one({
                'candidate_name': candidate_name,
                'recipient': recipient_email,
                'subject': f"Interview Assessment Report - {candidate_name}",
                'sent_at': datetime.now(timezone.utc),
                'email_id': email_id
            })
            
            print(f"Email sent successfully to {recipient_email} with ID {email_id}")
            return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == '__main__':
    app.run(debug=True)

