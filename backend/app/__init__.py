
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # Render PostgreSQL connection
    url = os.getenv("DATABASE_URL")
    # print("DATABASE_URL:", url)
    # app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    app.config['SQLALCHEMY_DATABASE_URI'] = url

    # Optional
    # app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Register blueprints here if any
    from .routes import main
    app.register_blueprint(main)

    return app