from sqlalchemy import Column, String, JSON, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class LocalInstance(Base):
    __tablename__ = "local_instances"

    instance_id = Column(String, primary_key=True)
    game_type = Column(String)
    status = Column(String)  # RUNNING, STOPPED, etc.
    save_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
