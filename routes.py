import requests
import random
from models import Server

import random
import logging
import os
import zipfile
import tempfile
from datetime import datetime
from flask import render_template, request, jsonify, redirect, url_for, Response, send_file, session, flash
from flask import current_app as app
from abilities import upload_file_to_storage, url_for_uploaded_file
from models import db, Upload, User
from werkzeug.security import generate_password_hash, check_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def register_routes(app):
    @app.route("/console/<server_id>/delete", methods=["DELETE"])
    def delete_server(server_id):
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        server = Server.query.get(server_id)
        if not server:
            return jsonify({"error": "Server not found"}), 404
            
        if server.user_id != session["user_id"]:
            return jsonify({"error": "Access denied"}), 403
            
        try:
            db.session.delete(server)
            db.session.commit()
            return jsonify({"message": "Server deleted successfully"})
        except Exception as e:
            logger.error(f"Error deleting server: {str(e)}")
            db.session.rollback()
            return jsonify({"error": "Failed to delete server"}), 500
    
    @app.route("/")
    def home_route():
        return render_template("home.html")
    
    @app.route("/console/<server_id>/files/list")
    def list_files(server_id):
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        try:
            files = Upload.query.filter_by(
                server_id=server_id,
                user_id=session["user_id"]
            ).order_by(Upload.created_at.desc()).all()
            
            file_list = []
            for file in files:
                file_list.append({
                    "id": file.id,
                    "filename": file.filename,
                    "size": file.size,
                    "created_at": file.created_at.strftime("%Y-%m-%d %H:%M:%S")
                })
            
            return jsonify({"files": file_list})
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return jsonify({"error": "Failed to list files"}), 500
    
    @app.route("/console/<server_id>/files/delete/<int:file_id>", methods=["DELETE"])
    def delete_file(server_id, file_id):
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        try:
            file = Upload.query.filter_by(
                id=file_id,
                server_id=server_id,
                user_id=session["user_id"]
            ).first()
            
            if not file:
                return jsonify({"error": "File not found"}), 404
            
            db.session.delete(file)
            db.session.commit()
            
            return jsonify({"message": "File deleted successfully"})
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return jsonify({"error": "Failed to delete file"}), 500
    
    @app.route("/console/<server_id>/files/download/<int:file_id>")
    def download_file(server_id, file_id):
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        try:
            file = Upload.query.filter_by(
                id=file_id,
                server_id=server_id,
                user_id=session["user_id"]
            ).first()
            
            if not file:
                return jsonify({"error": "File not found"}), 404
            
            file_url = url_for_uploaded_file(file.file_id)
            response = requests.get(file_url)
            
            return Response(
                response.content,
                mimetype="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={file.filename}"}
            )
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return jsonify({"error": "Failed to download file"}), 500

    @app.route("/console/<server_id>/files/edit/<int:file_id>", methods=["GET", "POST"])
    def edit_file(server_id, file_id):
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        try:
            file = Upload.query.filter_by(
                id=file_id,
                server_id=server_id,
                user_id=session["user_id"]
            ).first()
            
            if not file:
                return jsonify({"error": "File not found"}), 404
            
            if request.method == "POST":
                content = request.form.get("content")
                # TODO: Save the content back to the file storage
                return jsonify({"message": "File saved successfully"})
            
            # TODO: Load the file content from storage
            file_content = "Sample content"  # Placeholder
            return jsonify({"content": file_content})
        except Exception as e:
            logger.error(f"Error editing file: {str(e)}")
            return jsonify({"error": "Failed to edit file"}), 500

    @app.route("/forgot-password")
    def forgot_password_route():
        # For now, redirect to login with a message
        flash("Password reset functionality coming soon!")
        return redirect(url_for("login_route"))

    @app.route("/signup", methods=["GET", "POST"])
    def signup_route():
        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")
            
            errors = {}
            if not email:
                errors["email"] = "Email is required"
            if not password:
                errors["password"] = "Password is required"
            
            if errors:
                return render_template("signup.html", errors=errors)
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                errors["email"] = "Email already registered"
                return render_template("signup.html", errors=errors)
            
            # Create new user
            new_user = User(email=email)
            new_user.set_password(password)
            
            try:
                db.session.add(new_user)
                db.session.commit()
                # Log the user in after signup
                session["user_id"] = new_user.id
                session["email"] = new_user.email
                return redirect(url_for("panel_route"))
            except Exception as e:
                logger.error(f"Error creating user: {str(e)}")
                errors["general"] = "Error creating account. Please try again."
                return render_template("signup.html", errors=errors)
        
        return render_template("signup.html", errors={})

    @app.route("/login", methods=["GET", "POST"])
    def login_route():
        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")
            
            errors = {}
            user = User.query.filter_by(email=email).first()
            
            if not user or not user.check_password(password):
                errors["email"] = "Invalid email or password"
                return render_template("login.html", errors=errors)
            
            session["user_id"] = user.id
            session["email"] = user.email
            return redirect(url_for("panel_route"))
        
        return render_template("login.html", errors={})

    @app.route("/panel")
    def panel_route():
        if "user_id" not in session:
            return redirect(url_for("login_route"))
        
        # Get all servers for this user
        servers = Server.query.filter_by(user_id=session["user_id"]).all()
        
        # Delete any test servers
        for server in servers:
            if server.name == "Test Bot":
                db.session.delete(server)
        db.session.commit()
        
        # Refresh the server list after deletion
        servers = Server.query.filter_by(user_id=session["user_id"]).all()
        server_list = []
        
        for server in servers:
            server_list.append({
                "id": server.id,
                "name": server.name,
                "is_online": server.is_online,
                "cpu_usage": server.cpu_usage,
                "memory_usage": server.memory_usage
            })
        
        user = User.query.get(session["user_id"])
        if not user:
            session.clear()
            return redirect(url_for("login_route"))
        
        return render_template("panel.html", user=user, servers=server_list)

    @app.route("/create_server", methods=["POST"])
    def create_server():
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        server_name = request.json.get("server_name")
        server_type = request.json.get("server_type")
        
        if not server_name or not server_type:
            return jsonify({"error": "Server name and type are required"}), 400
        
        if server_type not in ["web", "bot"]:
            return jsonify({"error": "Invalid server type"}), 400
        
        if server_type == "bot":
            return jsonify({"error": "Bot hosting is currently under maintenance"}), 400
        
        # Generate a unique URL code for web servers
        url_code = Server.generate_url_code()
        while Server.query.filter_by(url_code=url_code).first():
            url_code = Server.generate_url_code()
        
        new_server = Server(
            name=server_name,
            server_type=server_type,
            user_id=session["user_id"],
            url_code=url_code,
            is_online=False  # Server starts as offline until files are uploaded
        )
        
        try:
            db.session.add(new_server)
            db.session.commit()
            
            # Create server data for the response
            server_data = {
                "id": new_server.id,
                "name": new_server.name,
                "is_online": False,
                "cpu_usage": 0,
                "memory_usage": 0,
                "url_code": url_code
            }
            
            return jsonify({
                "message": "Server created successfully",
                "server": server_data,
                "redirect_url": f"/success?url_code={url_code}"
            })
        except Exception as e:
            logger.error(f"Error creating server: {str(e)}")
            db.session.rollback()
            return jsonify({"error": "Failed to create server"}), 500

    @app.route("/logout")
    def logout_route():
        session.clear()
        return redirect(url_for("home_route"))

    @app.route("/console/<server_id>/stats")
    def server_stats(server_id):
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
            
        server = Server.query.get(server_id)
        if not server:
            return jsonify({"error": "Server not found"}), 404
            
        if server.user_id != session["user_id"]:
            return jsonify({"error": "Access denied"}), 403
            
        # Generate random stats for demo
        server.cpu_usage = round(random.uniform(0.1, 100.0), 1)
        server.memory_usage = round(random.uniform(50, 512.0), 1)
        
        # Calculate uptime
        uptime_delta = datetime.utcnow() - server.uptime
        hours = uptime_delta.seconds // 3600
        minutes = (uptime_delta.seconds % 3600) // 60
        uptime_str = f"{hours}h {minutes}m"
        
        db.session.commit()
        
        return jsonify({
            "cpu_usage": server.cpu_usage,
            "memory_usage": server.memory_usage,
            "uptime": uptime_str
        })
        
    @app.route("/console/<server_id>")
    def console_route(server_id):
        if "user_id" not in session:
            return redirect(url_for("login_route"))
        
        # Get the actual server from database
        server = Server.query.get(server_id)
        if not server:
            flash("Server not found")
            return redirect(url_for("panel_route"))
        
        # Verify server ownership
        if server.user_id != session["user_id"]:
            flash("Access denied")
            return redirect(url_for("panel_route"))
            
        # Get the most recent upload
        latest_upload = Upload.query.filter_by(
            server_id=str(server.id)
        ).order_by(Upload.created_at.desc()).first()
        
        # Calculate uptime
        uptime_delta = datetime.utcnow() - server.uptime
        hours = uptime_delta.seconds // 3600
        minutes = (uptime_delta.seconds % 3600) // 60
        uptime_str = f"{hours}h {minutes}m"
        
        db.session.commit()
        
        server_data = {
            "id": server.id,
            "name": server.name,
            "is_online": server.is_online,
            "url_code": server.url_code,
            "cpu_usage": round(server.cpu_usage, 1),
            "memory_usage": round(server.memory_usage, 1),
            "uptime": uptime_str,
            "console_output": [
                {"type": "success", "text": "[System] Server started successfully"},
                {"type": "", "text": "[Info] Website is live at /app/" + server.url_code},
                {"type": "", "text": "[Info] Latest upload: " + (latest_upload.filename if latest_upload else "No files uploaded yet")}
            ]
        }
        
        return render_template("console.html", server=server_data)
    
    @app.route("/console/<server_id>/files")
    def console_files_route(server_id):
        if "user_id" not in session:
            return redirect(url_for("login_route"))
        
        # Get files for this server
        files = Upload.query.filter_by(
            server_id=server_id,
            user_id=session["user_id"]
        ).order_by(Upload.created_at.desc()).all()
        
        server = {
            "id": server_id,
            "name": "Test Bot",
            "is_online": True,
            "files": [{
                "id": file.id,
                "name": file.filename,
                "size": file.size,
                "created_at": file.created_at.strftime("%Y-%m-%d %H:%M:%S")
            } for file in files]
        }
        
        return render_template("console_files.html", server=server)
    
    @app.route("/console/<server_id>/env")
    def console_env_route(server_id):
        if "user_id" not in session:
            return redirect(url_for("login_route"))
        
        # TODO: Get actual server data
        server = {
            "id": server_id,
            "name": "Test Bot",
            "is_online": True
        }
        
        return render_template("console_env.html", server=server)
        
    @app.route("/success")
    def success_route():
        url_code = request.args.get('url_code')
        if not url_code:
            return redirect(url_for("panel_route"))
        
        # Get server details
        server = Server.query.filter_by(url_code=url_code).first()
        if not server:
            logger.error(f"Server not found for url_code: {url_code}")
            return redirect(url_for("panel_route"))
            
        return render_template("upload_success.html", server=server)

    def format_size(size_in_bytes):
        """Convert size in bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} TB"

    @app.route("/console/<server_id>/upload", methods=["POST"])
    def upload_file(server_id):
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        logger.info(f"Processing file upload for server {server_id}")
        
        # Get server first to validate it exists and check ownership
        server = Server.query.get(server_id)
        if not server:
            logger.error(f"Server not found: {server_id}")
            return jsonify({"error": "Server not found"}), 404
        
        # Verify server ownership
        if server.user_id != session["user_id"]:
            logger.error(f"Access denied for server {server_id}")
            return jsonify({"error": "Access denied"}), 403
            
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        try:
            # Upload file to storage
            file_id = upload_file_to_storage(file)
            size = len(file.read())  # Get the size of the file
            file.seek(0)  # Reset file pointer
            
            # Create database entry
            upload = Upload(
                file_id=file_id,
                server_id=server_id,
                filename=file.filename,
                size=size,
                user_id=session["user_id"]
            )
            db.session.add(upload)
            # Set server as online
            server.is_online = True
            
            db.session.commit()
            logger.info(f"Upload record created with ID: {upload.id}")

            # Extract and validate zip content
            file_url = url_for_uploaded_file(file_id)
            response = requests.get(file_url)
            with tempfile.NamedTemporaryFile() as temp_file:
                temp_file.write(response.content)
                temp_file.seek(0)
                with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
                    if 'index.html' not in zip_ref.namelist():
                        return jsonify({"error": "Zip file must contain an index.html"}), 400

            website_url = f"/app/{server.url_code}"
            logger.info(f"Website is now accessible at: {website_url}")

            return jsonify({
                "message": "File uploaded successfully",
                "server": {
                    "id": server.id,
                    "name": server.name,
                    "is_online": True,
                    "website_url": website_url,
                    "redirect_url": f"/console/{server.id}"
                }
            })
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return jsonify({"error": "Failed to upload file"}), 500

    @app.route("/app/<url_code>", methods=["GET"])
    def serve_website(url_code):
        logger.info(f"Serving website for url_code: {url_code}")
        server = Server.query.filter_by(url_code=url_code).first()
        if not server:
            logger.error(f"Server not found for url_code: {url_code}")
            return "Website not found", 404
        
        if server.server_type != 'web':
            logger.error(f"Invalid server type: {server.server_type}")
            return "Invalid server type", 404
        
        # Get the most recent upload for this server
        upload = Upload.query.filter_by(
            server_id=str(server.id)
        ).order_by(Upload.created_at.desc()).first()
        
        if not upload:
            logger.warning(f"No files found for server {server.id}")
            return "No website files uploaded yet", 404
        
        logger.info(f"Found upload {upload.id} for server {server.id}")
        try:
            file_url = url_for_uploaded_file(upload.file_id)
            response = requests.get(file_url)
            
            with tempfile.NamedTemporaryFile() as temp_file:
                temp_file.write(response.content)
                temp_file.seek(0)
                
                with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
                    if 'index.html' not in zip_ref.namelist():
                        return "index.html not found in the uploaded zip", 404
                    # Extract index.html content
                    return zip_ref.read('index.html').decode('utf-8')
        except Exception as e:
            logger.error(f"Error serving website: {str(e)}")
            return "Error loading website", 500
