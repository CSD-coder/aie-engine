from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from ..core.config import get_settings
engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)
def get_session():
    with SessionLocal() as session: yield session
def init_db():
    from .models import Base
    Base.metadata.create_all(engine)
