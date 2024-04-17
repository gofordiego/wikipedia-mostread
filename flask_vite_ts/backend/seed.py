from app import create_app
from app.config import Config
from app.extensions import db
from app.models import SeedValue


SEED_DATA = [{"id": 1, "value": "one"}]


def seed_data():
    for item in SEED_DATA:
        seed_value = SeedValue(
            id=item["id"],
            value=item["value"],
        )
        print("==> Adding", seed_value.to_dict())
        db.session.add(seed_value)
        db.session.commit()

    records = db.session.execute(db.select(SeedValue)).all()
    print("==> Added count:", len(records))


if __name__ == "__main__":
    app = create_app(Config())
    with app.app_context():
        db.create_all()
        seed_data()
