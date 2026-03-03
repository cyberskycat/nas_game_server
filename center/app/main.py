from fastapi import FastAPI, HTTPException, Body, APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import uuid
from datetime import datetime
import os

from fastapi.staticfiles import StaticFiles
from . import schemas, repository, database

app = FastAPI(title="Game Server Edge Platform - Center")
api_router = APIRouter(prefix="/api")

# Initialize Database
@app.on_event("startup")
def on_startup():
    database.init_db()

@api_router.post("/nodes/register", response_model=schemas.Node)
async def register_node(data: schemas.NodeRegister, db: Session = Depends(database.get_db)):
    db_node = repository.create_or_update_node(db, data)
    return db_node

@api_router.post("/nodes/{node_id}/heartbeat")
async def heartbeat(
    node_id: str, 
    load_avg: float = Body(0.0, embed=True),
    running_instances: int = Body(0, embed=True),
    db: Session = Depends(database.get_db)
):
    db_node = repository.get_node(db, node_id)
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    repository.update_node_heartbeat(db, node_id, load_avg, running_instances)
    tasks = repository.get_pending_tasks(db, node_id)
    
    return {"status": "OK", "tasks": [schemas.Task.from_orm(t) for t in tasks]}

@api_router.post("/nodes/{node_id}/status")
async def update_node_status(
    node_id: str,
    status: str = Body(..., embed=True),
    db: Session = Depends(database.get_db)
):
    db_node = repository.get_node(db, node_id)
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    repository.update_node_status(db, node_id, status)
    return {"status": "UPDATED"}

@api_router.post("/games/deploy")
async def deploy_game(fmt: schemas.DeployRequest, db: Session = Depends(database.get_db)):
    node_id = fmt.node_id
    
    if node_id:
        db_node = repository.get_node(db, node_id)
        if not db_node:
            raise HTTPException(status_code=404, detail="Selected node not found")
        if db_node.status != "ONLINE":
            raise HTTPException(status_code=503, detail="Selected node is not ONLINE")
    else:
        nodes = repository.get_nodes(db)
        online_nodes = [n for n in nodes if n.status == "ONLINE"]
        if not online_nodes:
            raise HTTPException(status_code=503, detail="No available nodes")
        
        # Sort online nodes by last_seen (descending)
        online_nodes.sort(key=lambda n: n.last_seen, reverse=True)
        target_node = online_nodes[0]
        node_id = target_node.id
    
    instance_id = str(uuid.uuid4())
    
    # S3 config loader
    try:
        from .config import S3_ENABLED, S3_BUCKET, S3_PATH_PREFIX
    except (ImportError, ValueError):
        S3_ENABLED, S3_BUCKET, S3_PATH_PREFIX = False, "game-saves", "instances"

    if fmt.save_path:
        save_path = fmt.save_path
    elif S3_ENABLED:
        save_path = f"s3://{S3_BUCKET}/{S3_PATH_PREFIX}/{instance_id}.zip"
    else:
        save_path = f"local://tmp/game_saves/{instance_id}.zip"

    # Persist instance
    repository.create_instance(db, instance_id, node_id, fmt.game_type, fmt.owner_id, save_path)
    
    # Queue task for agent
    task_payload = {
        "instance_id": instance_id,
        "game_type": fmt.game_type,
        "env": {"INSTANCE_ID": instance_id, "EULA": "TRUE"},
        "save_path": save_path
    }
    repository.add_task(db, node_id, "DEPLOY", task_payload)
    
    return {"instance_id": instance_id, "node_id": node_id, "status": "QUEUED"}

@api_router.get("/instances", response_model=List[schemas.Instance])
async def list_instances(db: Session = Depends(database.get_db)):
    return repository.get_instances(db)

@api_router.post("/instances/{instance_id}/status")
async def update_instance_status(
    instance_id: str, 
    status: str = Body(..., embed=True), 
    details: str = Body(None, embed=True),
    db: Session = Depends(database.get_db)
):
    db_instance = repository.get_instance(db, instance_id)
    if not db_instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    repository.update_instance_status(db, instance_id, status, details)
    return {"status": "UPDATED"}

@api_router.post("/games/{instance_id}/stop")
async def stop_game(instance_id: str, db: Session = Depends(database.get_db)):
    db_instance = repository.get_instance(db, instance_id)
    if not db_instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    node_id = db_instance.node_id
    task_payload = {
        "instance_id": instance_id,
        "save_path": db_instance.save_path
    }
    repository.add_task(db, node_id, "STOP", task_payload)
    repository.update_instance_status(db, instance_id, "STOPPING")
    
    return {"status": "STOP_QUEUED"}

@api_router.get("/nodes", response_model=List[schemas.Node])
async def list_nodes(db: Session = Depends(database.get_db)):
    return repository.get_nodes(db)

app.include_router(api_router)

# Mount frontend if it exists
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
if os.path.exists(frontend_path):
    app.mount("/ui", StaticFiles(directory=frontend_path, html=True), name="ui")

@app.get("/")
async def root():
    return {"message": "Game Server Center is running. Visit /ui for dashboard."}
