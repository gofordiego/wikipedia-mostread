from sqlalchemy.orm import Mapped, mapped_column
from app.extensions import db


class SeedValue(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[str]

    def to_dict(self) -> dict[str, any]:
        return {
            "id": self.id,
            "value": self.value,
        }
