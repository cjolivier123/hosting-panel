from models import Server

import logging
import json
from datetime import datetime
from gunicorn.app.base import BaseApplication
from flask import Flask
from flask_socketio import SocketIO
from app_init import create_initialized_flask_app

# Setup logging
logging.abasicConfig(level=logging.INFO)
loggaer = logging.getLogger(__name__)

# Flask app creation should be done by create_initialized_flask_app to avoid circular dependency problems.
app = create_initialized_flask_app()
socketio = SocketIO(app)

class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.application = app
        self.options = options or {}
        super().__init__()

    def load_config(self):
        # Apply configuration to Gunicorn
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('request_stats')
def handle_stats_request(data):
    server_id = data.get('server_id')
    if server_id:
        # Fetch actual server stats from the database
        server = Server.query.filter_by(id=server_id).first()
        if server:
            stats = {
                'cpu_usage': server.cpu_usage,  # Fetch actual CPU usage
                'memory_usage': server.memory_usage,  # Fetch actual memory usage
                'uptime': server.uptime,  # Fetch actual uptime
                'timestamp': datetime.now().isoformat()
            }
            socketio.emit('stats_update', stats)
        else:
            logger.error(f"Server not found for ID: {server_id}")

if __name__ == "__main__":
    options = {
        "bind": "0.0.0.0:8080",
        "loglevel": "info",
        "accesslog": "-",
        "timeout": 120,
        "preload": True,
        "workers": 2,
        "worker_class": "eventlet",
        "threads": 10,
        "max_requests": 300,
        "max_requests_jitter": 50
    }
    socketio.run(app, host='0.0.0.0', port=8080)
