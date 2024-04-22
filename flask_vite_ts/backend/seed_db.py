from datetime import datetime

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import CachedResponse


SEED_DATA = [
    {
        "url": "http://localhost/test",
        "text_response": "Test",
        "created_at": datetime(1970, 1, 1, 0, 0, 0),
    }
]


def seed_data():
    for item in SEED_DATA:
        resp = CachedResponse(
            url=item["url"],
            text_response=item["text_response"],
            created_at=item["created_at"],
        )
        print("==> Adding", resp.to_dict())
        db.session.add(resp)
        db.session.commit()

    records = db.session.execute(db.select(CachedResponse)).all()
    print("==> Total added:", len(records))


if __name__ == "__main__":
    app = create_app(Config())
    with app.app_context():
        db.create_all()
        seed_data()
