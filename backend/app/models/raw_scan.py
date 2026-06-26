from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base


class RawScan(Base):
    __tablename__ = "raw_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    athlete_id: Mapped[int | None] = mapped_column(ForeignKey("athletes.id"), nullable=True)

    chip_number: Mapped[str | None] = mapped_column(String, nullable=True)

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    emit_total_time_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    emit_total_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    scanner_time_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    scanner_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    finish_to_scan_time_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    finish_to_scan_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    parse_status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
