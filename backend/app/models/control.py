from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base


class Control(Base):
    __tablename__ = "controls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    emit_code: Mapped[str | None] = mapped_column(String, nullable=True)

    is_finish: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("race_id", "sort_order", name="uq_control_race_sort_order"),
        UniqueConstraint("race_id", "emit_code", name="uq_control_race_emit_code"),
    )
