from sqlalchemy.orm import Mapped, mapped_column
import zlib

from app.extensions import db
from datetime import datetime


class CachedResponse(db.Model):
    """
    This is a basic URL to response caching model.

    Note:
        💡 By using zlib to compress the response text and store a BLOB
        instead of VARCHAR noticed a 10x reduction on the SQLite db file.
    """

    url: Mapped[str] = mapped_column(primary_key=True)
    compressed_response: Mapped[bytes]
    created_at: Mapped[datetime] = mapped_column(index=True)

    def __init__(self, url: str, text_response: str, created_at: datetime):
        """Convenience initializer to handle compression during model initialization."""
        compressed_response = zlib.compress(text_response.encode())
        super().__init__(
            url=url, compressed_response=compressed_response, created_at=created_at
        )

    @property
    def text_response(self) -> str:
        return zlib.decompress(self.compressed_response).decode()

    def to_dict(self) -> dict[str, any]:
        return {
            "url": self.url,
            "text_response": self.text_response,
            "created_at": self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
