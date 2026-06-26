from backend.app.database.session import Base, engine

# Import models here when they are created
# from backend.app.models.race import Race

def init_db() -> None:
    Base.metadata.create_all(bind=engine)
