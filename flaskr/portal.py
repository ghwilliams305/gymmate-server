import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)
from werkzeug.security import check_password_hash
import requests as req

from flaskr.db import get_db

bp = Blueprint('portal', __name__, url_prefix='/portal')

@bp.route('login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE email = ?', (email, )
        ).fetchone()

        if user is None:
            error = 'Incorrect E-mail'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect passoword'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return '' #Add Redict Location
        
        flash(error)

    return render_template('portal/login.html')

@bp.route('tos', methods=('GET', 'POST'))
def tos():
    return render_template('portal/tos.html')

@bp.route('privacy', methods=('GET', 'POST'))
def privacy():
    return render_template('portal/privacy.html')

@bp.route('home', methods=('GET', 'POST'))
def home():
    url = 'https://zenquotes.io/api/random'

    try:
        response = req.get(url)

        if response.status_code == 200:
            response_json = response.json()[0]
            quote_text = f""""{response_json['q']}" \n -{response_json['a']} (zenquotes.io)"""

            return render_template('portal/home.html', quote_text=quote_text)
        else:
            return render_template('portal/home.html', quote_text="Failed to get quote")
    except req.RequestException as e:
        return render_template('portal/home.html', quote_text=f"Failed to get quote {e}")

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id, )
        ).fetchone()

@bp.route('/logout')
def logout():
    session.clear()
    return '' #Add Redirect Location

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('portal.login'))
        
        return view(**kwargs)
    
    return wrapped_view