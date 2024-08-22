from datetime import datetime
import os
from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
from website.setup_scheduler import init_scheduler
from .setup_db import init_database, create_database
from .views import views
from .auth import auth
from . import models

load_dotenv()

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret_key")
    init_database(app)

    app.template_folder = "templates"

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    
    create_database(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = ""

    @login_manager.user_loader
    def load_user(id):
        return models.User.query.get((id))
    
    @app.template_filter('calculate_age')
    def calculate_age(date_of_birth):
        if date_of_birth:
            dob = datetime.strptime(date_of_birth, '%Y-%m-%d')
            today = datetime.now()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return age
        return None
    
    init_scheduler(app)

    return app
