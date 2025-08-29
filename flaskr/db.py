import sqlite3
import os
from datetime import datetime

import click
from flask import current_app, g
from cryptography.fernet import Fernet

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db

def get_id_key():
    if 'id_key' not in g:
        key_file = os.path.join(current_app.instance_path, 'id_key.txt')

        try:
            with open(key_file, "rb") as f:
                g.id_key = f.read()
        except FileNotFoundError:
            key = Fernet.generate_key()
            g.id_key = key
            with open(key_file, "wb") as f:
                f.write(key)

    return g.id_key

def encrypt_id(id):
    if not isinstance(id, int):
        raise ValueError(f'{id} is not an integer')
    
    key = get_id_key()
    fernet = Fernet(key)
    str_id = str(id)
    return fernet.encrypt(str_id.encode()).decode()

def decrypt_id(encrypt_id):
    if not isinstance(encrypt_id, str):
        raise ValueError(f'{encrypt_id} is not a string')

    key = get_id_key()
    fernet = Fernet(key)
    str_id = fernet.decrypt(encrypt_id.encode()).decode()
    return int(str_id)

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    db = get_db()
    key = get_id_key()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

@click.command('init-db')
def init_db_command():
    init_db()
    click.echo('Initialized the database.')

sqlite3.register_converter(
    "timestamp", lambda v: datetime.fromisoformat(v.decode())
)

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)