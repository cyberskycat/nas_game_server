from sqlalchemy import Column, String, Float, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Node(Base):
    __tablename__ = "nodes"

    id = Column(String, primary_key=True, index=True)
    hostname = Column(String)
    ip = Column(String)
    resources = Column(JSON)  # Stores {"cpu_cores": 4, "ram_gb": 16}
    status = Column(String, default="ONLINE")
    last_seen = Column(DateTime, default=datetime.utcnow)
    running_instances = Column(Integer, default=0)
    load_avg = Column(Float, default=0.0)
    public_key = Column(String, nullable=True)

class Instance(Base):
    __tablename__ = "instances"

    id = Column(String, primary_key=True, index=True)
    game_type = Column(String)
    owner_id = Column(String)
    node_id = Column(String, index=True)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    save_path = Column(String, nullable=True)
    details = Column(String, nullable=True)

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(String, index=True)
    type = Column(String)  # DEPLOY, STOP
    payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    consumed = Column(Integer, default=0) # 0: pending, 1: consumed

class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String)
    s3_path = Column(String)
    node_id = Column(String, index=True)
    instance_id = Column(String, index=True)
    file_size = Column(Integer)
    game_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Integer, default=0) # 0: False, 1: True for sqlite compat
