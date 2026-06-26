from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base


class EventLog(Base):
    __tablename__ = "event_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    race_id: Mapped[int | None] = mapped_column(ForeignKey("races.id"), nullable=True)
    severity: Mapped[str] = mapped_column(String, nullable=False)  # INFO, WARNING, ERROR
    source: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    related_scan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    related_athlete_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
