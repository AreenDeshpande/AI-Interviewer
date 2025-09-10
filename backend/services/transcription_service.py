import os
import uuid
import subprocess
import whisper


FFMPEG_PATH = os.getenv('FFMPEG_PATH', r"C:\\ffmpeg\\bin")
os.environ['PATH'] = FFMPEG_PATH + os.pathsep + os.environ.get('PATH', '')


def transcribe_audio(audio_file_path: str) -> str:
    try:
        if not os.path.exists(audio_file_path):
            return f"Error: Audio file not found at {audio_file_path}"

        audio_file_path = os.path.abspath(audio_file_path)
        file_size = os.path.getsize(audio_file_path)
        if file_size == 0:
            return 'Error: Audio file is empty (0 bytes)'

        wav_path = os.path.join(os.path.dirname(audio_file_path), f"whisper_temp_{uuid.uuid4().hex}.wav")
        ffmpeg_path = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
        ffmpeg_cmd = [ffmpeg_path, '-i', audio_file_path, '-ar', '16000', '-ac', '1', '-y', wav_path]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

        if not os.path.exists(wav_path):
            return 'Error: Failed to convert audio format'

        model = whisper.load_model('base')
        result = model.transcribe(wav_path)
        transcription = result.get('text', '').strip()
        if not transcription:
            transcription = 'No speech detected in audio recording'
        return transcription
    except subprocess.CalledProcessError as e:
        return f"Error during audio conversion: {e.stderr.decode() if e.stderr else str(e)}"
    except Exception as e:
        return f"Error during Whisper transcription: {str(e)}"
    finally:
        try:
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.remove(wav_path)
        except Exception:
            pass


def ffmpeg_info():
    try:
        ffmpeg_path = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
        exists = os.path.exists(ffmpeg_path)
        result = subprocess.run([ffmpeg_path, '-version'], capture_output=True, text=True)
        return {
            'ffmpeg_exists': exists,
            'ffmpeg_path': ffmpeg_path,
            'version_output': result.stdout,
            'status': 'FFmpeg is properly configured' if result.returncode == 0 else 'FFmpeg test failed',
            'return_code': result.returncode
        }
    except Exception as e:
        import traceback
        return {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'status': 'FFmpeg test failed'
        }


