import os

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)
from werkzeug.security import check_password_hash, generate_password_hash
from authlib.integrations.flask_client import OAuth

from flaskr.db import get_db, encrypt_id

bp = Blueprint('google', __name__, url_prefix='/google')
oauth = OAuth()

def register_google_oauth():
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
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

@bp.route('/google/')
def google():
    redirect_uri = url_for('google.google_auth', _external=True)
    nonce = os.urandom(16).hex()
    session['nonce'] = nonce
    return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)

@bp.route('/google/auth/')
def google_auth():
    token = oauth.google.authorize_access_token()
    nonce = session.pop('nonce', None)
    google_user = oauth.google.parse_id_token(token, nonce)
    username = f'google_user:{encrypt_id(int(google_user['sub']))}'
    db = get_db()
    error = None
    user = db.execute(
        'SELECT * FROM user WHERE username = ?', (username, )
    ).fetchone()

    if user is None:
        error = 'No google account'
        print(error)
        print('username', username)

    if error is None:
        session.clear()
        session['user_id'] = user['id']
        return '' #Add Redict Location

    flash(error)
    return redirect(url_for('portal.login'))