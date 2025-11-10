import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)
from werkzeug.security import check_password_hash

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