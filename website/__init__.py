from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
import os
from flask_login import LoginManager

from flask_dropzone import Dropzone
basedir = os.path.abspath(path.dirname(__file__))

db = SQLAlchemy()
DB_NAME = "database.db"

dropzone = Dropzone()

#Aye's Code Start


def create_app():
    app = Flask(__name__)
    
    app.config['UPLOADED_PATH']  = os.path.join(basedir,'uploads')
    app.config['DOPZONE_MAX_FILE_SIZE'] = 1024
    app.config['DROPZONE_TIMEOUT'] = 5*60*1000

    dropzone.init_app(app)



    app.config['SECRET_KEY'] = 'hash123'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    from .views import views
    from .auth import auth
    from .gpt import gpt

    app.register_blueprint(views, url_prefix='')
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(gpt, url_prefix='/gpt')

    from .models import User, Note
    
    with app.app_context():
        db.create_all()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    if not path.exists('website/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')
