import functools
import os

from cryptography.fernet import Fernet
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)
from werkzeug.security import check_password_hash, generate_password_hash

from flaskr.db import get_db, encrypt_id, decrypt_id

def row_to_matrix(row):
    try:
        matrix = [
            [row['a'], row['b'], row['c']],
            [row['d'], row['e'], row['f']],
            [row['g'], row['h'], row['i']],
            [row['j'], row['k'], row['l']],
            [row['m'], row['n'], row['o']]
        ]

        return matrix
    except:
        raise ValueError(f'{row} is an invaild input')

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/signup', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"message": "Invalid or no JSON data received"}), 400
        name = data['name']
        username = data['username']
        email = data['email']
        password = data['password']
        db = get_db()
        error = None

        if not username:
            error = 'Username is required'
        elif not name:
            error = 'Name is required'
        elif not email:
            error = 'E-mail is required'
        elif not password:
            error = 'Password is required'

        if error is None:
            try:
                db.execute(
                    "INSERT INTO user (name, username, email, password) VALUES (?, ?, ?, ?)",
                    (name, username, email, generate_password_hash(password))
                )
                db.commit()
            except db.IntegrityError:
                error = f'User {username} or E-mail {email} is already registered'
            else:
                user = db.execute(
                    'SELECT * FROM user WHERE username = ?', (username, )
                ).fetchone()

                db.execute(
                    "INSERT INTO user_info (user_id, body_weight, height, daily_rate, experience, k, goal) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user['id'], data['bodyWeight'], data['height'], data['dailyRate'], data['experience'], data['k'], data['goal'])
                )
                db.execute(
                    "INSERT INTO user_matrix (user_id) VALUES (?)",
                    (user['id'], )
                )
                for week_day in data['week_days']:
                    db.execute(
                        "INSERT INTO user_days VALUES (?, ?)",
                        (user['id'], week_day)
                    )
                for equipment in data['equipment']:
                    db.execute(
                        "INSERT INTO user_equipment VALUES (?, ?)",
                        (user['id'], equipment)
                    )
                db.commit()
                
                del data['password']
                data['id'] = encrypt_id(user['id'])

                return jsonify(data)

        return jsonify({"message": error}), 400

    return 'signup'

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"message": "Invalid or no JSON data received"}), 400
        email = data['email'] 
        password = data['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE email = ?', (email, )
        ).fetchone()

        if user is None:
            error = 'Incorrect username'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password'

        if error is None:
            user_info = db.execute(
                "SELECT * FROM user_info WHERE user_id = ?",
                (user['id'], )
            ).fetchone()
            raw_matrix = db.execute(
                "SELECT * FROM user_matrix WHERE user_id = ?",
                (user['id'], )
            ).fetchone()
            matrix = row_to_matrix(raw_matrix)
            week_days = []
            raw_week_days = db.execute(
                "SELECT week_day FROM user_days WHERE user_id = ?",
                (user['id'], )
            ).fetchall()
            for raw_week_day in raw_week_days:
                week_days.append(raw_week_day['week_day'])
            equipment = []
            raw_tools = db.execute(
                "SELECT equipment FROM user_equipment WHERE user_id = ?",
                (user['id'], )
            ).fetchall()
            for raw_tool in raw_tools:
                equipment.append(raw_tool['equipment'])
            
            user_dict = dict(user)
            del user_dict['password']
            user_dict['id'] = encrypt_id(user['id'])
            user_dict.update(dict(user_info))
            del user_dict['user_id']
            user_dict['matrix'] = matrix
            user_dict['week_days'] = week_days
            user_dict['equipment'] = equipment

            return jsonify(user_dict)

        return jsonify({"message": error}), 400

    return 'login'

@bp.route('/save', methods=('GET', 'POST'))
def save_profile():
    if request.method == 'POST':
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"message": "Invalid or no JSON data received"}), 400
        user_id = decrypt_id(data['id'])
        db = get_db()
        user = db.execute(
            'SELECT * FROM user WHERE id = ?', (user_id, )
        ).fetchone()
        error = None

        if not user:
            error = 'ID not found'

        if error is None:
            try:
                db.execute(
                    'UPDATE user SET name = ?, username = ?, email = ? WHERE id = ?',
                    (data['name'], data['username'], data['email'], user_id)
                )
                db.commit()
            except db.IntegrityError:
                error = f'User {data["username"]} or E-mail {data["email"]} is already registered'
            else:
                db.execute(
                    'UPDATE user_info SET body_weight = ?, height = ?, daily_rate = ?, experience = ?, A = ?, B = ?, C = ?, I = ?, k = ?, goal = ?, work_time = ? WHERE user_id = ?',
                    (data['bodyWeight'], data['height'], data['dailyRate'], data['experience'], data['A'], data['B'], data['C'], data['I'], data['k'], data['goal'], data['work_time'], user_id)
                )
                flatten_matrix = [item for sub_list in data['matrix'] for item in sub_list]
                flatten_matrix.append(user_id)
                db.execute(
                    "UPDATE user_matrix SET a = ?, b = ?, c = ?, d = ?, e = ?, f = ?, g = ?, h = ?, i = ?, j = ?, k = ?, l = ?, m = ?, n = ?, o = ? WHERE user_id = ?",
                    tuple(flatten_matrix)
                )
                db.execute('DELETE FROM user_days WHERE user_id = ?', (user_id, ))
                db.execute('DELETE FROM user_equipment WHERE user_id = ?', (user_id, ))
                db.commit()
                for week_day in data['week_days']:
                    db.execute(
                        "INSERT INTO user_days VALUES (?, ?)",
                        (user_id, week_day)
                    )
                for equipment in data['equipment']:
                    db.execute(
                        "INSERT INTO user_equipment VALUES (?, ?)",
                        (user_id, equipment)
                    )
                db.commit()

                return jsonify(data)

        return jsonify({"message": error}), 400

    return 'save'

@bp.route('/password', methods=('GET', 'POST'))
def new_password():
    if request.method == 'POST':
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"message": "Invalid or no JSON data received"}), 400
        
        user_id = decrypt_id(data['id'])
        new_password = data['new_password'] 
        password = data['password']
        db = get_db()
        error = None
        user_password = db.execute(
            'SELECT password FROM user WHERE id = ?', (user_id, )
        ).fetchone()['password']

        if user_password is None:
            error = 'Bad ID'
        elif not check_password_hash(user_password, password):
            error = 'Incorrect password'

        if error is None:
            db.execute(
                'UPDATE user SET password = ? WHERE id = ?',
                (generate_password_hash(new_password), user_id)
            )
            db.commit()

            return jsonify(data)

        return jsonify({"message": error}), 400

    return 'password'

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view