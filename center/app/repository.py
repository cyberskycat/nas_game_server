from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime
import uuid

def get_node(db: Session, node_id: str):
    return db.query(models.Node).filter(models.Node.id == node_id).first()

def get_nodes(db: Session):
    return db.query(models.Node).all()

def create_or_update_node(db: Session, node: schemas.NodeRegister):
    node_id = node.node_id or str(uuid.uuid4())
    db_node = db.query(models.Node).filter(models.Node.id == node_id).first()
    
    if db_node:
        db_node.hostname = node.hostname
        db_node.ip = node.ip
        db_node.resources = node.resources
        db_node.status = "ONLINE"
        db_node.last_seen = datetime.utcnow()
        if node.public_key:
            db_node.public_key = node.public_key
    else:
        db_node = models.Node(
            id=node_id,
            hostname=node.hostname,
            ip=node.ip,
            resources=node.resources,
            status="ONLINE",
            last_seen=datetime.utcnow(),
            public_key=node.public_key
        )
        db.add(db_node)
    
    db.commit()
    db.refresh(db_node)
    return db_node

def update_node_status(db: Session, node_id: str, status: str):
    db_node = db.query(models.Node).filter(models.Node.id == node_id).first()
    if db_node:
        db_node.status = status
        db.commit()
        db.refresh(db_node)
    return db_node

def update_node_heartbeat(db: Session, node_id: str, load_avg: float, running_instances: int, resources: dict = None):
    db_node = db.query(models.Node).filter(models.Node.id == node_id).first()
    if db_node:
        db_node.status = "ONLINE" # Ensure it's ONLINE on heartbeat
        db_node.last_seen = datetime.utcnow()
        db_node.load_avg = load_avg
        db_node.running_instances = running_instances
        if resources:
            db_node.resources = resources
        db.commit()
        db.refresh(db_node)
    return db_node

def create_instance(db: Session, instance_id: str, node_id: str, game_type: str, owner_id: str, save_path: str):
    db_instance = models.Instance(
        id=instance_id,
        node_id=node_id,
        game_type=game_type,
        owner_id=owner_id,
        status="PROVISIONING",
        save_path=save_path
    )
    db.add(db_instance)
    db.commit()
    db.refresh(db_instance)
    return db_instance

def get_instance(db: Session, instance_id: str):
    return db.query(models.Instance).filter(models.Instance.id == instance_id).first()

def get_active_instance_count(db: Session, node_id: str):
    return db.query(models.Instance).filter(
        models.Instance.node_id == node_id,
        models.Instance.status.in_(["PROVISIONING", "RUNNING"])
    ).count()

def get_instances(db: Session):
    return db.query(models.Instance).all()

def update_instance_status(db: Session, instance_id: str, status: str, details: str = None):
    db_instance = db.query(models.Instance).filter(models.Instance.id == instance_id).first()
    if db_instance:
        db_instance.status = status
        db_instance.updated_at = datetime.utcnow()
        if details:
            db_instance.details = details
        db.commit()
        db.refresh(db_instance)
    return db_instance

def add_task(db: Session, node_id: str, task_type: str, payload: dict):
    db_task = models.Task(
        node_id=node_id,
        type=task_type,
        payload=payload
    )
    db.add(db_task)
    db.commit()
    return db_task

def get_pending_tasks(db: Session, node_id: str):
    tasks = db.query(models.Task).filter(
        models.Task.node_id == node_id,
        models.Task.consumed == 0
    ).all()
    
    # Mark as consumed
    for t in tasks:
        t.consumed = 1
    db.commit()
    return tasks

def update_instance_save_path(db: Session, instance_id: str, new_path: str):
    instance = db.query(models.Instance).filter(models.Instance.id == instance_id).first()
    if instance:
        instance.save_path = new_path
        db.commit()
    return instance

def create_uploaded_file(db: Session, file_id: str, filename: str, s3_path: str, node_id: str, instance_id: str, file_size: int, game_type: str):
    db_file = models.UploadedFile(
        id=file_id,
        filename=filename,
        s3_path=s3_path,
        node_id=node_id,
        instance_id=instance_id,
        file_size=file_size,
        game_type=game_type
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def get_active_uploaded_files(db: Session):
    return db.query(models.UploadedFile).filter(models.UploadedFile.is_deleted == 0).all()

def get_uploaded_files(db: Session):
    return db.query(models.UploadedFile).order_by(models.UploadedFile.created_at.desc()).all()

def mark_uploaded_file_deleted(db: Session, file_id: str):
    db_file = db.query(models.UploadedFile).filter(models.UploadedFile.id == file_id).first()
    if db_file:
        db_file.is_deleted = 1
        db.commit()
    return db_file
