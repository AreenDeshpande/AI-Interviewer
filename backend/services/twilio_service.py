import os
from twilio.rest import Client
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VideoGrant
from twilio.base.exceptions import TwilioRestException


TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_API_KEY = os.getenv('TWILIO_API_KEY')
TWILIO_API_SECRET = os.getenv('TWILIO_API_SECRET')

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def create_interview_room(interview_id: str, user_id: str) -> dict:
    room_name = f"interview-{interview_id}"
    try:
        try:
            room = twilio_client.video.v1.rooms(room_name).fetch()
        except TwilioRestException as e:
            if e.status == 404:
                room = twilio_client.video.v1.rooms.create(
                    unique_name=room_name,
                    type='group',
                    record_participants_on_connect=False,
                    status_callback=f"https://yourserver.com/room-callback/{interview_id}",
                    max_participants=3
                )
            else:
                raise e

        token = AccessToken(TWILIO_ACCOUNT_SID, TWILIO_API_KEY, TWILIO_API_SECRET, identity=f"user-{user_id}")
        video_grant = VideoGrant(room=room_name)
        token.add_grant(video_grant)
        jwt_token = token.to_jwt()
        if isinstance(jwt_token, bytes):
            jwt_token = jwt_token.decode()
        return {'room_name': room_name, 'user_token': jwt_token}
    except Exception as e:
        raise e


def create_token_for_room(room_name: str, identity: str) -> str:
    token = AccessToken(TWILIO_ACCOUNT_SID, TWILIO_API_KEY, TWILIO_API_SECRET, identity=identity)
    video_grant = VideoGrant(room=room_name)
    token.add_grant(video_grant)
    jwt_token = token.to_jwt()
    if isinstance(jwt_token, bytes):
        jwt_token = jwt_token.decode()
    return jwt_token


