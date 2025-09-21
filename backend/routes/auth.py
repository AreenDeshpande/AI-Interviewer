import os
from datetime import datetime, timedelta, timezone
from flask import Blueprint, current_app, request, jsonify
from bson import ObjectId
import bcrypt
import jwt


auth_bp = Blueprint('auth', __name__, url_prefix='/api')


def token_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            token = token.split(' ')[1]
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = current_app.db.users.find_one({'_id': ObjectId(data['user_id'])})
            if not current_user:
                return jsonify({'message': 'Invalid token!'}), 401
        except Exception:
            return jsonify({'message': 'Invalid token!'}), 401
        return fn(current_user, *args, **kwargs)

    return wrapper


@auth_bp.post('/register')
def register():
    db = current_app.db
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


@auth_bp.post('/login')
def login():
    db = current_app.db
    data = request.get_json()
    user = db.users.find_one({'email': data['email']})

    if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), user['password']):
        return jsonify({'message': 'Invalid credentials'}), 401

    token = jwt.encode({
        'user_id': str(user['_id']),
        'exp': datetime.now(timezone.utc) + timedelta(days=1)
    }, current_app.config['SECRET_KEY'])

    return jsonify({
        'token': token,
        'user': {
            'id': str(user['_id']),
            'email': user['email'],
            'name': user.get('name', '')
        }
    })


