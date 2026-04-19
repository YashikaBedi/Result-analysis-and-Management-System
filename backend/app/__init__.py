import os
import platform
import socket
import pymysql

# Workaround for Windows WMI hang during platform detection used by SQLAlchemy imports
if os.name == 'nt':
    def safe_machine():
        return os.environ.get('PROCESSOR_ARCHITECTURE', 'AMD64')

    def safe_processor():
        return os.environ.get('PROCESSOR_IDENTIFIER', '')

    def safe_win32_ver(*args, **kwargs):
        return ('10', '10.0.0', '', 'Multiprocessor Free')

    platform.machine = safe_machine
    platform.processor = safe_processor
    platform.win32_ver = safe_win32_ver

# Install pymysql as MySQLdb for compatibility
pymysql.install_as_MySQLdb()

from flask import Flask, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_name=None):
    """Application factory"""
    # Define paths for the new split structure
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
    template_dir = os.path.join(frontend_dir, "templates")
    static_dir = os.path.join(frontend_dir, "static")

    app = Flask(__name__, 
                template_folder=template_dir, 
                static_folder=static_dir)

    @app.before_request
    def log_request():
        print('DEBUG: before_request', request.method, request.path)
    
    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    from config import config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Register blueprints
    from app.routes import auth_bp, dashboard_bp, results_bp, analytics_bp, admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(admin_bp)
    
    # Root route redirect
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))
    
    
    # Database commands
    @app.cli.command()
    def init_db():
        """Initialize the database."""
        db.create_all()
        print('Initialized the database.')
    
    @app.cli.command()
    def drop_db():
        """Drop all database tables."""
        if input('Are you sure? Type "yes" to confirm: ') == 'yes':
            db.drop_all()
            print('Dropped all tables.')
    
    # Request context for user loader
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    return app
