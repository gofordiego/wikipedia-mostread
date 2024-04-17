from unittest import TestCase, main
import os
import sys
from tempfile import TemporaryDirectory

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.config import Config
from app.extensions import db


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


if __name__ == "__main__":
    main()