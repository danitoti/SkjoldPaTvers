from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base


class Athlete(Base):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)

    start_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chip_number: Mapped[str | None] = mapped_column(String, nullable=True)

    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    club: Mapped[str | None] = mapped_column(String, nullable=True)

    gender: Mapped[str | None] = mapped_column(String, nullable=True)
    class_name: Mapped[str | None] = mapped_column(String, nullable=True)
    distance: Mapped[str | None] = mapped_column(String, nullable=True)

    country: Mapped[str | None] = mapped_column(String, nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    eqtiming_participant_uid: Mapped[str | None] = mapped_column(String, nullable=True)
    eqtiming_athlete_uid: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("race_id", "start_number", name="uq_athlete_race_start_number"),
        UniqueConstraint("race_id", "chip_number", name="uq_athlete_race_chip_number"),
    )
