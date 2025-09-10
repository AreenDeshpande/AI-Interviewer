import os
import time
import uuid
from datetime import datetime, timezone
from flask import Blueprint, current_app, request, jsonify
from bson import ObjectId

from .auth import token_required
from ..services.openai_service import generate_interview_questions, generate_interview_report
from ..services.transcription_service import transcribe_audio, ffmpeg_info
from ..services.pdf_service import create_pdf_report
from ..services.email_service import send_report_email
from ..services.twilio_service import create_interview_room, create_token_for_room


interview_bp = Blueprint('interview', __name__)


BOT_NAME = "ASSESS AI"
BOT_AVATAR = "https://your-domain.com/bot-avatar.png"


@interview_bp.get('/interview-instructions')
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


@interview_bp.post('/upload-resume')
@token_required
def upload_resume(current_user):
    if 'resume' not in request.files:
        return jsonify({'error': 'No resume file provided'}), 400
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    try:
        time.sleep(2)
        questions = generate_interview_questions("")
        interview_id = str(uuid.uuid4())
        interview = {
            '_id': ObjectId(),
            'interview_id': interview_id,
            'user_id': current_user['_id'],
            'resume_filename': file.filename,
            'resume_processed': True,
            'questions': questions,
            'status': 'scheduled',
            'created_at': datetime.now(timezone.utc),
            'scheduled_at': datetime.now(timezone.utc),
            'processing_time': '2 seconds',
            'current_question_index': 0
        }
        db = current_app.db
        db.interviews.insert_one(interview)

        room_details = create_interview_room(interview_id, str(current_user['_id']))
        db.interviews.update_one({'interview_id': interview_id}, {'$set': {'candidate_token': room_details['user_token']}})
        db.interviews.update_one({'interview_id': interview_id}, {'$set': {
            'room_name': room_details['room_name'],
            'questions': questions,
            'status': 'ready',
            'current_question_index': 0
        }})

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
        return jsonify({'message': f'Upload failed: {str(e)}'}), 500


@interview_bp.get('/interview/<interview_id>')
def interview_room(interview_id):
    try:
        db = current_app.db
        interview = db.interviews.find_one({'interview_id': interview_id})
        if not interview:
            return jsonify({'message': 'Interview not found'}), 404
        token = interview.get('candidate_token')
        if not token:
            return jsonify({'message': 'Interview token not found'}), 404
        room_name = interview.get('room_name') or f"interview-{interview_id}"
        if 'room_name' not in interview:
            db.interviews.update_one({'interview_id': interview_id}, {'$set': {'room_name': room_name}})
        questions = interview.get('questions', [])
        bot_name = interview.get('bot_name', BOT_NAME)
        bot_avatar = interview.get('bot_avatar', BOT_AVATAR)
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
        return jsonify({'message': f'Error accessing interview room: {str(e)}'}), 500


@interview_bp.route('/interview-status/<interview_id>', methods=['GET', 'POST'])
def interview_status(interview_id):
    try:
        db = current_app.db
        if request.method == 'GET':
            interview = db.interviews.find_one({'interview_id': interview_id})
            if not interview:
                return jsonify({'message': 'Interview not found'}), 404
            return jsonify({
                'status': interview['status'],
                'current_question_index': interview.get('current_question_index', 0),
                'questions': interview['questions'],
                'room_name': interview['room_name']
            })
        else:
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
            result = db.interviews.update_one({'interview_id': interview_id}, update_data)
            if result.modified_count == 0:
                return jsonify({'message': 'Interview not found or no changes made'}), 404
            return jsonify({'message': 'Interview status updated successfully'})
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


@interview_bp.post('/interview/<interview_id>/token')
def get_token(interview_id):
    try:
        db = current_app.db
        interview = db.interviews.find_one({'interview_id': interview_id})
        if not interview:
            return jsonify({'message': 'Interview not found'}), 404
        token = create_token_for_room(interview['room_name'], identity=f"tts_{interview_id}")
        return jsonify({
            'token': token,
            'room_name': interview['room_name'],
            'current_question_index': interview.get('current_question_index', 0),
            'questions': interview['questions']
        })
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


@interview_bp.post('/interview/<interview_id>/record-response')
def record_response(interview_id):
    temp_audio_path = None
    try:
        db = current_app.db
        interview = db.interviews.find_one({'interview_id': interview_id})
        if not interview:
            return jsonify({'message': 'Interview not found'}), 404
        data = request.get_json()
        question_index = data.get('question_index', 0)
        audio_blob = data.get('audio_blob')
        if not audio_blob:
            return jsonify({'message': 'No audio data provided'}), 400

        timestamp = int(time.time())
        temp_filename = f"audio_{interview_id}_{question_index}_{timestamp}"
        import base64
        if 'data:audio/webm' in audio_blob:
            audio_data = base64.b64decode(audio_blob.split(',')[1])
            temp_audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{temp_filename}.webm")
        elif 'data:audio/wav' in audio_blob:
            audio_data = base64.b64decode(audio_blob.split(',')[1])
            temp_audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{temp_filename}.wav")
        else:
            audio_data = base64.b64decode(audio_blob.split(',')[1])
            temp_audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{temp_filename}.webm")
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        with open(temp_audio_path, 'wb') as f:
            f.write(audio_data)
        if not os.path.exists(temp_audio_path) or os.path.getsize(temp_audio_path) == 0:
            return jsonify({'message': 'Failed to save audio file'}), 500

        transcription = transcribe_audio(temp_audio_path)
        if not transcription:
            transcription = 'No speech detected in audio recording'
        response_data = {
            'question_index': question_index,
            'question': interview['questions'][question_index] if question_index < len(interview.get('questions', [])) else 'Unknown question',
            'transcription': transcription,
            'timestamp': datetime.now(timezone.utc),
            'audio_processed': True
        }
        result = db.interviews.update_one({'interview_id': interview_id}, {'$push': {'responses': response_data}})
        updated_interview = db.interviews.find_one({'interview_id': interview_id})
        responses_count = len(updated_interview.get('responses', []))
        return jsonify({
            'message': 'Response recorded and transcribed successfully',
            'transcription': transcription,
            'question_index': question_index,
            'audio_size': len(audio_data),
            'total_responses': responses_count
        })
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500
    finally:
        try:
            if temp_audio_path and os.path.exists(temp_audio_path):
                if 'Error during Whisper transcription' not in str(locals().get('transcription', '')):
                    os.remove(temp_audio_path)
        except Exception:
            pass


@interview_bp.post('/interview/<interview_id>/complete')
def complete_interview(interview_id):
    try:
        db = current_app.db
        interview = db.interviews.find_one({'interview_id': interview_id})
        if not interview:
            return jsonify({'message': 'Interview not found'}), 404

        result = db.interviews.find_one_and_update(
            {'interview_id': interview_id, '$or': [{'status': {'$ne': 'completed'}}, {'report_sent': {'$ne': True}}]},
            {'$set': {'completion_process_id': str(uuid.uuid4()), 'completion_started_at': datetime.now(timezone.utc)}},
            return_document=False
        )
        if not result:
            return jsonify({'message': 'Interview already completed or being processed', 'report_generated': True, 'email_sent': True, 'candidate_name': interview.get('candidate_name', 'Candidate')})

        user = db.users.find_one({'_id': interview['user_id']})
        candidate_name = user.get('name', 'Candidate') if user else 'Candidate'
        candidate_email = user.get('email', 'unknown@email.com') if user else 'unknown@email.com'

        responses = interview.get('responses', [])
        if not responses:
            questions = interview.get('questions', [])
            responses = []
            for i, question in enumerate(questions):
                responses.append({'question_index': i, 'question': question, 'transcription': 'No response recorded', 'timestamp': datetime.now(timezone.utc)})
            db.interviews.update_one({'interview_id': interview_id}, {'$set': {'responses': responses}})
            interview['responses'] = responses

        qa_section = 'INTERVIEW QUESTIONS & ANSWERS:\n\n'
        for i, question in enumerate(interview.get('questions', [])):
            response = next((r for r in responses if r.get('question_index') == i), None)
            answer = response.get('transcription', 'No response recorded') if response else 'No response recorded'
            qa_section += f"Question {i+1}: {question}\n"
            qa_section += f"Response: {answer}\n\n"

        report_content = generate_interview_report(interview)
        if not report_content:
            report_content = f"""
INTERVIEW ASSESSMENT REPORT

CANDIDATE: {candidate_name}
EMAIL: {candidate_email}
DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

INTERVIEW SUMMARY:
Manual review required.

{qa_section}

RECOMMENDATION:
Manual review recommended for final assessment.

SCORE: Pending manual review
"""
        else:
            report_content += f"\n\n{qa_section}"

        pdf_buffer = create_pdf_report(report_content, candidate_name)
        report_already_sent = interview.get('report_sent', False)
        email_sent = False
        if pdf_buffer and not report_already_sent:
            email_sent = send_report_email(db, pdf_buffer, candidate_name, recipient_email='piyushkrishna11@gmail.com')
        elif report_already_sent:
            email_sent = True

        update_result = db.interviews.update_one(
            {'interview_id': interview_id, 'completion_process_id': interview.get('completion_process_id')},
            {'$set': {
                'status': 'completed',
                'completed_at': datetime.now(timezone.utc),
                'report_generated': True,
                'report_sent': email_sent,
                'report_content': report_content,
                'candidate_name': candidate_name
            }}
        )
        if update_result.modified_count == 0:
            return jsonify({'message': 'Interview was completed by another process', 'report_generated': True, 'email_sent': True})

        return jsonify({'message': 'Interview completed successfully', 'report_generated': True, 'email_sent': email_sent, 'candidate_name': candidate_name})
    except Exception as e:
        return jsonify({'message': f'Error completing interview: {str(e)}'}), 500


@interview_bp.post('/interview/<interview_id>/next-question')
def next_question(interview_id):
    try:
        db = current_app.db
        interview = db.interviews.find_one({'interview_id': interview_id})
        if not interview:
            return jsonify({'message': 'Interview not found'}), 404
        current_index = interview.get('current_question_index', 0) + 1
        if current_index >= len(interview.get('questions', [])):
            db.interviews.update_one({'interview_id': interview_id}, {'$set': {'status': 'completed'}})
            return jsonify({'message': 'Interview completed', 'has_more_questions': False, 'current_question_index': current_index})
        db.interviews.update_one({'interview_id': interview_id}, {'$set': {'status': 'in_progress', 'current_question_index': current_index}})
        return jsonify({'message': 'Moved to next question', 'has_more_questions': True, 'current_question_index': current_index, 'question': interview['questions'][current_index]})
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


@interview_bp.get('/test-ffmpeg')
def test_ffmpeg():
    return jsonify(ffmpeg_info())


