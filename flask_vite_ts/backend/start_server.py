import logging

from app import create_app
from app.config import Config

if __name__ == "__main__":
    logging.basicConfig(
        format="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    app = create_app(config=Config())
    app.run(host="127.0.0.1", port=8080, debug=True, threaded=True)
