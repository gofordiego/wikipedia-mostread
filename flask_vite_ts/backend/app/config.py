import os

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URI"
    ) or "sqlite:///" + os.path.join(basedir, "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True
    # Safeguard timeout to return a meaningful error message if an async function
    # is taking longer to complete before the server closes the connection.
    SERVER_TIMEOUT_SECS = 60
