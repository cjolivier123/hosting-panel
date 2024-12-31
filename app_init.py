from routes import app

import os
import logging
from flask import Flask
from sqlalchemy.engine import Engine
from sqlalchemy import event

from abilities import apply_sqlite_migrations
from models import db
from routes import register_routes


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_initialized_flask_app():
    app = Flask(__name__, static_folder='static')

    # Set Flask secret key
    app.config['SECRET_KEY'] = 'supersecretflaskskey'

    # Initialize database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
    db.init_app(app)

    # Apply database migrations
    with app.app_context():
        apply_sqlite_migrations(db.engine, db.Model, 'migrations')

    def format_size(size_in_bytes):
        """Convert size in bytes to human readable format"""
        if not isinstance(size_in_bytes, (int, float)):
            return "0 B"
        size_in_bytes = float(size_in_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} TB"

    app.jinja_env.filters['format_size'] = format_size
    register_routes(app)

    return app
