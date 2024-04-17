from app import create_app
from app.config import Config

if __name__ == "__main__":
    app = create_app(config=Config())
    app.run(host="127.0.0.1", port=8080, debug=True, threaded=True)
