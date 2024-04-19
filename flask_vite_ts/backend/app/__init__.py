import asyncio
from flask import Flask, jsonify, request
from flask_cors import CORS
from typing import Coroutine

from app.config import Config
from app.extensions import db
from shared.wiki_api import WikiAPI


def create_app(config: Config):
    app = Flask(__name__)
    app.config.from_object(config)

    # Flask SQLAlchemy: https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/quickstart/#initialize-the-extension
    db.init_app(app)

    # Cross-origin resource sharing
    CORS(app, expose_headers=["X-Total-Count"])

    wiki_api = WikiAPI()

    @app.route("/")
    def home():
        name = request.args.get("name", "world")
        result = {"data": f"hello {name}"}
        status_code = 200
        return jsonify(result), status_code

    @app.route("/most_read_articles")
    def most_read_articles():
        lang_code = request.args.get("lang_code", "")
        start = request.args.get("start", "")
        end = request.args.get("end", "")

        result = asyncio.run(
            _run_timed_task(
                coro=wiki_api.fetch_most_read_articles(lang_code, start, end),
                timeout=app.config["SERVER_TIMEOUT_SECS"],
            )
        )

        status_code = 200 if not "request_error" in result else 400
        return jsonify(result), status_code

    @app.route("/test_timeout")
    def test_timeout():
        timeout_seconds = 1

        async def delay(seconds: int):
            await asyncio.sleep(seconds)

        result = asyncio.run(
            _run_timed_task(
                coro=delay(timeout_seconds + 1),
                timeout=timeout_seconds,
            )
        )

        return jsonify(result)

    return app


async def _run_timed_task(coro: Coroutine, timeout: int) -> dict[str, any]:
    """"""
    try:
        async with asyncio.timeout(timeout):
            return await coro
    except TimeoutError:
        return _json_format_error("The server took too long to complete the task.")
    except Exception as e:
        return _json_format_error(str(e))


def _json_format_error(message: str) -> dict[str, str]:
    return {"request_error": message}
