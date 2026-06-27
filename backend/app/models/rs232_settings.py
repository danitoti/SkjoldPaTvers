from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String

from backend.app.database.session import Base


class Rs232Settings(Base):
    __tablename__ = "rs232_settings"

    id = Column(Integer, primary_key=True)
    selected_race_id = Column(Integer, ForeignKey("races.id"), nullable=True)
    port = Column(String(255), nullable=True)
    baudrate = Column(Integer, nullable=False, default=9600)
    timeout_seconds = Column(Float, nullable=False, default=1.0)
    is_enabled = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
