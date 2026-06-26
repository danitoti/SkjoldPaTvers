from backend.app.database.session import Base, engine

# Import models so SQLAlchemy registers them before create_all()
from backend.app.models.race import Race  # noqa: F401
from backend.app.models.event_log import EventLog  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
