import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from pymongo import MongoClient


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)

    # Core config
    app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-here')
    app.config['MONGODB_URI'] = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/ai_interviewer')
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # Ensure uploads dir
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # CORS (match existing frontend origin)
    CORS(app, resources={
        r"/*": {
            "origins": ["http://localhost:5173"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    # Database
    mongo_client = MongoClient(app.config['MONGODB_URI'])
    app.mongo_client = mongo_client
    app.db = mongo_client.ai_interviewer

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.interview import interview_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(interview_bp)

    # Health route
    @app.get('/health')
    def health() -> dict:
        return {"status": "ok"}

    return app


