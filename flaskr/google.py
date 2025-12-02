import os
import jwt
 
from urllib.parse import quote
from datetime import datetime, timezone, timedelta

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)
from werkzeug.security import check_password_hash, generate_password_hash
from authlib.integrations.flask_client import OAuth

from flaskr.db import get_db

bp = Blueprint('google', __name__, url_prefix='/google')
oauth = OAuth()

def register_google_oauth():
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'

    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url=CONF_URL,
        client_kwargs={'scope': 'openid email profile'}
    )

@bp.before_app_request
def setup_oauth():
    register_google_oauth()

@bp.route('/portal')
def portal_google():
    redirect_uri = url_for('google.portal_google_auth', _external=True)
    nonce = os.urandom(16).hex()
    session['nonce'] = nonce
    return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)

@bp.route('/portal/auth/')
def portal_google_auth():
    token = oauth.google.authorize_access_token()
    nonce = session.pop('nonce', None)
    error = None
    if nonce is None:
        error = 'Invalid session (nonce missing)'

    if error is None:
        try:
            google_user = oauth.google.parse_id_token(token, nonce)
            username = f"google_user:{google_user['sub']}"
            db = get_db()
            error = None
            user = db.execute(
                'SELECT * FROM user WHERE username = ?', (username, )
            ).fetchone()

            print(google_user)
            if user is None:
                error = 'No google account'
                print(error)
                print('username', username)
        except Exception as e:
            error = f'Invalid google user: {e}'

    if error is None:
        session.clear()
        session['user_id'] = user['id']
        return '' #Add Redict Location

    flash(error)
    return redirect(url_for('portal.login'))

@bp.route('/android')
def android_google():
    redirect_uri = url_for('google.android_google_auth', _external=True)
    nonce = os.urandom(16).hex()
    session['nonce'] = nonce
    return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)

@bp.route('/android/auth/')
def android_google_auth():
    token = oauth.google.authorize_access_token()
    nonce = session.pop('nonce', None)
    error = None
    if nonce is None:
        error = 'Invalid session (nonce missing)'

    if error is None:
        try:
            google_user = oauth.google.parse_id_token(token, nonce)
            google_id = int(google_user['sub'])
            email = google_user['email']
            name = google_user['name']

            JWT_SECRET = os.getenv('JWT_SECRET')
            now = datetime.now(timezone.utc)
            payload = {
                'sub': google_id,
                'name': name,
                'email': email,
                'iat': now,
                'exp': now + timedelta(minutes=15)
            }
            jwt_token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
            print(jwt_token)
        except Exception as e:
            error = f'Invalid google login: {e}'

    if error is None:
        return redirect(f"gymmateapp://auth?token={jwt_token}")
    
    print(error)
    return redirect(f"gymmateapp://auth?error={quote(error)}")