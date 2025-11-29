import os

from flask import Flask, request, redirect, url_for
from cryptography.fernet import Fernet
from authlib.integrations.flask_client import OAuth

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='685a83021836f61f69d93dd775af517b18b753d8501ac4385c7be4ead70a6788',
        SERVER_NAME='localhost:5000',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route('/')
    def enterance():
        return redirect(url_for('portal.home'))

    @app.route('/error')
    def hello():
        if request.method == 'GET':
            error_message = request.args.get('error_message', default='', type=str)

            import smtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg.set_content(error_message)
            msg['Subject'] = 'Gymmate App Crash'
            msg['From'] = 'lk27auggee@gmail.com'
            msg['To'] = 'contact@gymmateapp.net'

            smtp_server = "smtp.gmail.com"
            port = 587

            with smtplib.SMTP(smtp_server, port) as server:
                server.starttls()
                server.login("lk27auggee@gmail.com", "ihuu qirm adae hwpc")
                server.send_message(msg)

            return 'successful'

        return 'error'

    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import workout
    app.register_blueprint(workout.bp)

    from . import portal
    app.register_blueprint(portal.bp)

    from . import google
    google.oauth.init_app(app)
    app.register_blueprint(google.bp)

    return app