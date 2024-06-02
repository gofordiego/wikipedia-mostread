import asyncio
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from typing import Coroutine

from app.config import Config
from app.extensions import db
from app.models import CachedResponse
from shared.wiki_api import WikiAPI, WikiCache, WikiAPIResponse


class ResponseCache(WikiCache):
    """This is a subclass of WikiCache used to store WikiAPI responses in a SQLite db.

    Note:
        `CachedResponse` model stores text responses as a zlib compressed BLOB value.
    """

    def __init__(self) -> None:
        super().__init__()

    def get(self, url: str) -> WikiAPIResponse:
        cached_resp = db.session.get(CachedResponse, url)
        if cached_resp:
            return WikiAPIResponse(
                cached_resp.url, True, cached_resp.text_response, None
            )
        return None

    def put(self, wiki_resp: WikiAPIResponse):
        # No point in storing erroneous or empty responses.
        if wiki_resp.exception or not wiki_resp.status_ok or not len(wiki_resp.text):
            return

        # Insert or replace cached_resp.
        cached_resp = CachedResponse(
            url=wiki_resp.url,
            text_response=wiki_resp.text,
            created_at=datetime.now(),
        )
        db.session.merge(cached_resp)
        db.session.commit()


def create_app(config: Config) -> Flask:
    """This functions prepares the Flask app environment and returns it."""

    app = Flask(__name__)
    app.config.from_object(config)

    # Flask SQLAlchemy: https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/quickstart/#initialize-the-extension
    db.init_app(app)

    # Cross-origin resource sharing
    CORS(app)

    # Wiki API client with caching and rate limiting.
    wiki_api = WikiAPI(optional_cache=ResponseCache())

    @app.route("/")
    def home():
        example_query = (
            "/most_read_articles?lang_code=en&start=2024-02-28&end=2024-02-28"
        )
        return f"""
            Example query:
                <a href="{example_query}">{example_query}</a>
        """

    @app.route("/most_read_articles")
    def most_read_articles():
        lang_code = request.args.get("lang_code", "")
        start = request.args.get("start", "")
        end = request.args.get("end", "")

        result = asyncio.run(
            run_timed_task(
                coro=wiki_api.fetch_most_read_articles(lang_code, start, end),
                timeout=app.config["SERVER_TIMEOUT_SECS"],
            )
        )

        status_code = 200 if not "request_error" in result else 400
        return jsonify(result), status_code

    return app


async def run_timed_task(coro: Coroutine, timeout: int) -> dict[str, any]:
    """This function stops running `coro` after `timeout` and reports any error message."""
    try:
        async with asyncio.timeout(timeout):
            return await coro
    except TimeoutError:
        return _json_format_error("The server took too long to complete the task.")
    except Exception as e:
        return _json_format_error(str(e))


def _json_format_error(message: str) -> dict[str, str]:
    return {"request_error": message}
