from sqlalchemy.orm import Session
from . import models
from datetime import datetime

def get_local_instance(db: Session, instance_id: str):
    return db.query(models.LocalInstance).filter(models.LocalInstance.instance_id == instance_id).first()

def get_local_instances(db: Session):
    return db.query(models.LocalInstance).all()

def create_or_update_instance(db: Session, instance_id: str, game_type: str, status: str, save_path: str):
    db_instance = db.query(models.LocalInstance).filter(models.LocalInstance.instance_id == instance_id).first()
    if db_instance:
        db_instance.status = status
        db_instance.save_path = save_path
        db_instance.updated_at = datetime.utcnow()
    else:
        db_instance = models.LocalInstance(
            instance_id=instance_id,
            game_type=game_type,
            status=status,
            save_path=save_path
        )
        db.add(db_instance)
    db.commit()
    db.refresh(db_instance)
    return db_instance

def remove_instance(db: Session, instance_id: str):
    db_instance = db.query(models.LocalInstance).filter(models.LocalInstance.instance_id == instance_id).first()
    if db_instance:
        db.delete(db_instance)
        db.commit()
    return True
