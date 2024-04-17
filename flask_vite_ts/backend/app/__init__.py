from flask import Flask, jsonify, request
from flask_cors import CORS

from app.config import Config
from app.extensions import db


def create_app(config: Config):
    app = Flask(__name__)
    app.config.from_object(config)

    # Flask SQLAlchemy: https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/quickstart/#initialize-the-extension
    db.init_app(app)

    # Cross-origin resource sharing
    CORS(app, expose_headers=["X-Total-Count"])

    @app.route("/")
    def home():
        name = request.args.get("name", "world")
        result = {"data": f"hello {name}"}
        status_code = 200
        return jsonify(result), status_code

    return app
