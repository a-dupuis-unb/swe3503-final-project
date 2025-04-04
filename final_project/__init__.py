# This file initializes the Flask application
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Initialize SQLAlchemy without an app (will be attached to app later)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'main.login'  # Updated to use blueprint prefix

def create_app(config=None):
    app = Flask(__name__)
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///finance.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'supersecretkey')
    
    # Configuration for encryption
    app.config['MASTER_KEY'] = os.getenv('MASTER_KEY', 'defaultmasterkey')  # This should be securely set in production
    
    # Initialize extensions with app
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Import models to ensure they are known to Flask-Migrate
    from . import models
    
    # Register blueprints
    from final_project.app import bp as main_bp
    app.register_blueprint(main_bp)
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))
    
    # Add template context processors if needed
    @app.context_processor
    def utility_processor():
        return {
            'app_name': 'Expense Tracker'
        }
        
    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return "Page not found", 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return "Internal server error", 500
    
    # Create database tables in development mode
    if app.config.get('ENV') == 'development':
        with app.app_context():
            db.create_all()
    
    return app
