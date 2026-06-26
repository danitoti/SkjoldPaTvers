from sqlalchemy import Boolean, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base


class ResultSplit(Base):
    __tablename__ = "result_splits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), nullable=False)
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id"), nullable=False)

    source_scan_punch_id: Mapped[int | None] = mapped_column(
        ForeignKey("scan_punches.id"),
        nullable=True,
    )

    has_punch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    time_from_start_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    split_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("result_id", "control_id", name="uq_result_split_result_control"),
    )
