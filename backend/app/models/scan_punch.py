from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base


class ScanPunch(Base):
    __tablename__ = "scan_punches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    raw_scan_id: Mapped[int] = mapped_column(ForeignKey("raw_scans.id"), nullable=False)

    control_id: Mapped[int | None] = mapped_column(ForeignKey("controls.id"), nullable=True)

    emit_code: Mapped[str | None] = mapped_column(String, nullable=True)
    sequence_code: Mapped[str | None] = mapped_column(String, nullable=True)

    split_time_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    split_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    accumulated_time_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    accumulated_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    calculated_time_from_start_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    ignored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ignore_reason: Mapped[str | None] = mapped_column(String, nullable=True)
