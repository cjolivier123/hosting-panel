import os
import logging
import uuid
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String(255), nullable=False)
    server_id = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('uploads', lazy=True))

class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    server_type = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    url_code = db.Column(db.String(50), unique=True, nullable=True)
    is_online = db.Column(db.Boolean, default=False)
    cpu_usage = db.Column(db.Float, default=0.0)
    memory_usage = db.Column(db.Float, default=0.0)
    uptime = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('servers', lazy=True))

    @staticmethod
    def generate_url_code():
        return str(uuid.uuid4())[:8]
