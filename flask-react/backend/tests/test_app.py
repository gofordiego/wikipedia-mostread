import asyncio
from datetime import datetime
import json
import os
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase, main

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, run_timed_task, ResponseCache
from app.config import Config
from app.extensions import db
from app.models import CachedResponse
from shared.wiki_api import WikiAPIResponse
from tests.shared.expected_results_wiki_api import (
    EXPECTED_MOST_READ_ES_20240219,
)


class TestApp(TestCase):

    def setUp(self):
        self.temp_db_file = os.path.join(
            TemporaryDirectory(delete=False).name, "app.db"
        )

        config = Config()
        config.SQLALCHEMY_DATABASE_URI = "sqlite:///" + self.temp_db_file
        print(f"==> setUp created temp_db_file={self.temp_db_file}")

        app = create_app(config)
        app.testing = True

        with app.app_context():
            db.create_all()

        self.app = app
        self.client = app.test_client()

    def tearDown(self):
        os.remove(self.temp_db_file)
        os.rmdir(os.path.dirname(self.temp_db_file))
        print(f"==> tearDown removed temp_db_file={self.temp_db_file}")

    # MARK: - Endpoint Tests

    def test_home(self):
        expected_response = """
            Example query:
                <a href="/most_read_articles?lang_code=en&start=2024-02-28&end=2024-02-28">/most_read_articles?lang_code=en&start=2024-02-28&end=2024-02-28</a>
        """
        response = self.client.get("/")
        self.assertEqual(response.text.strip(), expected_response.strip())

    def test_most_read_articles_success(self):
        test_cached_url = (
            "https://es.wikipedia.org/api/rest_v1/feed/featured/2024/02/20"
        )
        params = {"lang_code": "es", "start": "2024-02-19", "end": "2024-02-19"}
        expected_status_code = 200
        expected_data = EXPECTED_MOST_READ_ES_20240219

        # Test CachedResponse Empty
        with self.app.app_context():
            self.assertIsNone(db.session.get(CachedResponse, test_cached_url))

        # Test API Fetch
        response = self.client.get("/most_read_articles", query_string=params)
        self.assertEqual(response.status_code, expected_status_code)
        self.assertEqual(response.json, expected_data)

        # Test CachedResponse Stored
        with self.app.app_context():
            cached_response = db.session.get(CachedResponse, test_cached_url)
            self.assertEqual(
                json.loads(cached_response.text_response)["mostread"]["date"],
                "2024-02-19Z",
            )

    def test_most_read_articles_error(self):
        params = {"lang_code": "en", "start": "2024-01-14", "end": "2024-01-13"}
        expected_status_code = 400
        expected_data = {
            "request_error": "Invalid date range, start date should be before the end date."
        }

        response = self.client.get("/most_read_articles", query_string=params)

        self.assertEqual(response.status_code, expected_status_code)
        self.assertEqual(response.json, expected_data)

    # MARK: - run_timed_task Tests

    def test_run_timed_task_timeout(self):
        async def delay(seconds: int):
            await asyncio.sleep(seconds)

        expected_result = {
            "request_error": "The server took too long to complete the task."
        }
        test_timeout_seconds = 1
        result = asyncio.run(
            run_timed_task(
                coro=delay(test_timeout_seconds + 1),
                timeout=test_timeout_seconds,
            )
        )
        self.assertEqual(result, expected_result)

    # MARK: - ResponseCache Tests

    def test_response_cache(self):
        # Using app_context to fetch db session.
        with self.app.app_context():
            cache = ResponseCache()

            test_url = "test_url"
            test_response = "Test"

            # Test Cache Miss
            self.assertIsNone(cache.get(test_url))

            # Test Cache Put
            before_put_time = datetime.now()
            cache.put(WikiAPIResponse(test_url, True, test_response, None))

            first_put_time = db.session.get(CachedResponse, test_url).created_at
            self.assertGreater(first_put_time, before_put_time)

            # Test Cache Hit
            wiki_resp = cache.get(test_url)
            self.assertEqual(wiki_resp.url, test_url)
            self.assertTrue(wiki_resp.status_ok)
            self.assertEqual(wiki_resp.text, test_response)
            self.assertIsNone(wiki_resp.exception)

            # Test Cache Update
            cache.put(WikiAPIResponse(test_url, True, test_response, None))

            wiki_resp = cache.get(test_url)
            self.assertEqual(wiki_resp.text, test_response)

            second_put_time = db.session.get(CachedResponse, test_url).created_at
            self.assertGreater(second_put_time, first_put_time)


if __name__ == "__main__":
    main()
