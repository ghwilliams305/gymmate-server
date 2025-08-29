import functools
import os
import io
import base64

from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import numpy as np

from cryptography.fernet import Fernet
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)
from werkzeug.security import check_password_hash, generate_password_hash

from flaskr.db import get_db, encrypt_id, decrypt_id

bp = Blueprint('workout', __name__, url_prefix='/workout')

@bp.route('/save', methods=('GET', 'POST'))
def log_workout():
    if request.method == 'POST':
        workout_dict = request.get_json(silent=True)
        if workout_dict is None:
            return jsonify({"message": "Invalid or no JSON data received"}), 400
        user_id =  decrypt_id(workout_dict['user_id'])
        db = get_db()
        error = None

        if not user_id:
            error = 'ID not found'

        if error is None:
            try:
                db.execute(
                    'INSERT INTO workout_data (user_id, title, time, intensity, goal, volume) VALUES (?, ?, ?, ?, ?, ?)', 
                    (user_id, workout_dict['title'], workout_dict['time'], workout_dict['intensity'], workout_dict['goal'], workout_dict['volume'])
                )
                db.commit()
            except db.IntegrityError:
                error = f'User {user_id} is already registered'
            else:
                workout_id = db.execute('SELECT id FROM workout_data ORDER BY id DESC').fetchone()['id']
                flatten_matrix = [item for sub_list in workout_dict['output_matrix'] for item in sub_list]
                flatten_matrix.insert(0, workout_id)
                db.execute(
                    'INSERT INTO workout_matrix (workout_data_id, a, b, c, d, e, f, g, h, i, j, k, l, m, n, o) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    tuple(flatten_matrix)
                )
                for equipment in workout_dict['equipment']:
                    db.execute(
                        'INSERT INTO workout_equipment (workout_data_id, equipment) VALUES (?, ?)',
                        (workout_id, equipment)
                    )

                workout_exercises = workout_dict['workout']
                for exercise in workout_exercises:
                    (sets, weight, reps, volume, time, rating) = workout_exercises[exercise]
                    weight = weight * (1 + reps / 30)
                    intensity = workout_dict['intensity'] * (rating / 3)
                    db.execute(
                        'INSERT INTO exercise_data (workout_data_id, user_id, name, time, intensity, weight, sets, reps, rating, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (workout_id, user_id, exercise, time, intensity, weight, sets, reps, rating, volume)
                    )

                db.commit()

                return jsonify(workout_dict)

        return jsonify({"message": error}), 400

    return 'save'

@bp.route('/exercise_rating', methods=('GET', 'POST'))
def get_exercise_rating():
    if request.method == 'GET':
        exercise_name = request.args.get('name', default='', type=str)
        error = None
        db = get_db()

        if not exercise_name:
            error = 'Request needs name param'

        if error is None:
            try:
                response = db.execute(
                    """
                    SELECT AVG(rating) AS avg_rating
                    FROM exercise_data
                    WHERE name = ?
                    """,
                    (exercise_name, )).fetchone()
                
                if response['avg_rating'] is None:
                    return jsonify({'avg_rating': 3})

                response = dict(response)

                return jsonify(response)
            except:
                pass

        return jsonify({"message": error}), 400

    return 'exercise_rating'

@bp.route('/set_data', methods=('GET', 'POST'))
def set_data():
    if request.method == 'GET':
        user_id = request.args.get('id', default='', type=str)
        error = None
        reponse = {}
        db = get_db()
        
        if not user_id:
            error = 'Request needs user id'

        if error is None:
            user_id = decrypt_id(user_id)
            
            workout_data = db.execute(
                """
                SELECT *
                FROM workout_data
                WHERE user_id = ?
                LIMIT 30
                """, 
                (user_id, )).fetchall()
            if not workout_data:
                reponse = {'message': 'Not entries'}
                return jsonify(reponse), 404

            workout_data = list(workout_data)
            workout_data = [dict(row) for row in workout_data]

            exercise_data = db.execute(
                """
                SELECT *
                FROM exercise_data
                WHERE user_id = ?
                LIMIT 30
                """, 
                (user_id, )).fetchall()
            exercise_data = list(exercise_data)
            exercise_data = [dict(row) for row in exercise_data]

            workout_ids = [workout['id'] for workout in workout_data]
            placeholder = ', '.join("?" for _ in workout_ids)
            print(workout_ids, placeholder)
            workout_equipment = db.execute(
                f"""
                SELECT *
                FROM workout_equipment
                WHERE workout_data_id IN ({placeholder})
                LIMIT 30
                """, 
                tuple(workout_ids)).fetchall()
            workout_equipment = list(workout_equipment)
            workout_equipment = [dict(row) for row in workout_equipment]
            workout_matrix = db.execute(
                f"""
                SELECT *
                FROM workout_matrix
                WHERE workout_data_id IN ({placeholder})
                LIMIT 30
                """, 
                tuple(workout_ids)).fetchall()
            workout_matrix = list(workout_matrix)
            workout_matrix = [dict(row) for row in workout_matrix]

            reponse = {
                'workout_data': workout_data,
                'exercise_data': exercise_data,
                'workout_equipment': workout_equipment,
                'workout_matrix': workout_matrix
            }
            print(reponse)
            return jsonify(reponse)

        reponse = {'message': error}
        return jsonify(reponse), 400

    return 'set_data'

@bp.route('/graphs', methods=('GET', 'POST'))
def get_graphs():
    if request.method == 'POST':
        report = request.get_json(silent=True)
        if report is None:
            return jsonify({"message": "Invalid or no JSON data received"}), 400

        graphs = {
            'figure': io.BytesIO(),
            'matrix_figure': io.BytesIO(),
            'matrix_graph': io.BytesIO()
        }

        try:
            fig, ax = plt.subplots()
            fig.set_facecolor('#0E0B16')
            ax.set_facecolor('#0E0B16')
            ax.grid(color='#B0B0B0')
            ax.plot(report['strength_data'], marker='o', color='#8F00FF')
            ax.spines['bottom'].set_color('#FFFFFF')
            ax.spines['left'].set_color('#FFFFFF')
            plt.title('Strength', color='#FFFFFF')
            plt.ylim(bottom=0)
            plt.tick_params(axis='y', labelleft=False)
            plt.tick_params(axis='x', labelbottom=False)
            plt.savefig(graphs['figure'], format='jpeg')

            fig, ax = plt.subplots()
            fig.set_facecolor('#0E0B16')
            ax.set_facecolor('#0E0B16')
            ax.grid(axis='x', color='#B0B0B0')
            ax.barh(report['muscle_data'].keys(), report['muscle_data'].values(), color='#8F00FF')
            ax.spines['bottom'].set_color('#FFFFFF')
            ax.spines['left'].set_color('#FFFFFF')
            plt.title('Strength per muscle', color='#FFFFFF')
            plt.ylim(bottom=-1)
            plt.tick_params(axis='y', colors='#FFFFFF')
            plt.tick_params(axis='x', labelbottom=False)
            plt.savefig(graphs['matrix_graph'], format='jpeg')

            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
            fig.set_facecolor('#0E0B16')
            Z = np.array(report['user_matrix'])
            rows, cols = Z.shape
            x = np.arange(cols)
            y = np.arange(rows)
            X, Y = np.meshgrid(x, y)
            ax.plot_surface(X, Y, Z, cmap='viridis', edgecolor='none')
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_zticks([])
            ax.grid(False)
            ax.set_facecolor('#0E0B16')
            plt.savefig(graphs['matrix_figure'], format='jpeg')

            graphs['figure'] = base64.b64encode(graphs['figure'].getvalue()).decode('utf-8')
            graphs['matrix_figure'] = base64.b64encode(graphs['matrix_figure'].getvalue()).decode('utf-8')
            graphs['matrix_graph'] = base64.b64encode(graphs['matrix_graph'].getvalue()).decode('utf-8')

            return jsonify(graphs)
        except Exception as e:
            return jsonify({'message': e}), 500

    return 'graphs'

@bp.route('/k_value', methods=('GET', 'POST'))
def get_k_value():
    if request.method == 'POST':
        raw_data = request.get_json(silent=True)
        if raw_data is None:
            return jsonify({"message": "Invalid or no JSON data received"}), 400

        volumes = raw_data['volumes']
        times = raw_data['times']
        intensities = raw_data['intensities']
        workout_dict = raw_data['workout_dict']

        try:
            k = 0
            if len(raw_data) > 10:
                volumes.append(workout_dict['volume'])
                times.append(workout_dict['time'])
                intensities.append(workout_dict['intensity'])
                e = np.array(volumes)
                t = np.array(times)
                I = np.array(intensities)
                X = (I * t ).reshape(-1, 1)
                y = e
                model = LinearRegression()
                model.fit(X, y)
                k = model.coef_[0] ** 5

            return jsonify({'k': k})
        except Exception as e:
            return jsonify({'message': e}), 500

    return 'k_value'