import os
import sqlite3
import shutil
import logging
from datetime import datetime
from gunicorn.app.base import BaseApplication
from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from models import db, Server
from routes import register_routes

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create storage directory if it doesn't exist
os.makedirs('storage', exist_ok=True)

# Create Flask app
app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'supersecretflaskskey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
db.init_app(app)
socketio = SocketIO(app)

def init_db():
    """Initialize the database with the latest schema"""
    try:
        # Get the list of migration files
        migration_files = sorted([f for f in os.listdir('migrations') if f.endswith('.sql')])
        
        # Connect to the database
        conn = sqlite3.connect('your_database.db')
        cursor = conn.cursor()
        
        # Create migrations table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Get list of applied migrations
        cursor.execute('SELECT filename FROM migrations')
        applied_migrations = {row[0] for row in cursor.fetchall()}
        
        # Apply new migrations
        for filename in migration_files:
            if filename not in applied_migrations:
                logger.info(f"Applying migration: {filename}")
                
                # Read and execute the migration file
                with open(os.path.join('migrations', filename)) as f:
                    migration_sql = f.read()
                    cursor.executescript(migration_sql)
                
                # Record the migration
                cursor.execute('INSERT INTO migrations (filename) VALUES (?)', (filename,))
                conn.commit()
        
        conn.close()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

# Initialize database before first request
with app.app_context():
    init_db()

# Register routes
register_routes(app)

# Serve manifest.json
@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=8080)
