from flask import Blueprint, jsonify
from . import db
from sqlalchemy import text

main = Blueprint('main', __name__)

@main.route("/")
def home():
    return jsonify({"message": "Hello from Flask!"})

@main.route('/test-db')
def test_db():
    with db.engine.connect() as conn:
        result = conn.execute(text("SELECT NOW()"))
        return f"Database time: {list(result)[0][0]}"