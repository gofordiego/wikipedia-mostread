import json
import os
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase, main

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.config import Config
from app.extensions import db
from tests.shared.expected_results_wiki_api import (
    EXPECTED_MOST_READ_ES_20240219,
)


class TestServer(TestCase):

    def setUp(self):
        self.temp_db_file = os.path.join(
            TemporaryDirectory(delete=False).name, "app.db"
        )

        config = Config()
        config.SQLALCHEMY_DATABASE_URI = "sqlite:///" + self.temp_db_file
        print("TestServer.setUp temp_db_file=", self.temp_db_file)

        app = create_app(config)
        app.testing = True

        with app.app_context():
            db.create_all()

        self.app = app
        self.client = app.test_client()

    def tearDown(self):
        print("TestServer.tearDown removing temp_db_file=", self.temp_db_file)
        os.remove(self.temp_db_file)
        os.rmdir(os.path.dirname(self.temp_db_file))

    def test_hello(self):
        response = self.client.get("/")
        self.assertEqual(response.json, {"data": "hello world"})

        response = self.client.get("/?name=diego")
        self.assertEqual(response.json, {"data": "hello diego"})

    def test_most_read_articles_success(self):
        params = {"lang_code": "es", "start": "2024-02-19", "end": "2024-02-19"}

        expected_status_code = 200
        expected_data = EXPECTED_MOST_READ_ES_20240219

        response = self.client.get("/most_read_articles", query_string=params)

        self.assertEqual(response.status_code, expected_status_code)
        self.assertEqual(response.json, expected_data)

    def test_most_read_articles_error(self):
        params = {"lang_code": "en", "start": "2024-01-14", "end": "2024-01-13"}
        expected_status_code = 400
        expected_data = {
            "request_error": "Invalid date range, start date should be before the end date."
        }

        response = self.client.get("/most_read_articles", query_string=params)

        self.assertEqual(response.status_code, expected_status_code)
        self.assertEqual(response.json, expected_data)

    def test_timeout(self):
        response = self.client.get("/test_timeout")
        expected_data = {
            "request_error": "The server took too long to complete the task."
        }
        self.assertEqual(response.json, expected_data)


if __name__ == "__main__":
    main()
