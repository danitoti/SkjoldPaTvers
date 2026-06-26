from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base


class Result(Base):
    __tablename__ = "results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), nullable=False)

    source_raw_scan_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_scans.id"),
        nullable=True,
    )

    total_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    missing_controls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[str] = mapped_column(String, default="ok", nullable=False)
    note: Mapped[str | None] = mapped_column(String, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("race_id", "athlete_id", name="uq_result_race_athlete"),
    )
