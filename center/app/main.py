from fastapi import FastAPI, HTTPException, Body, APIRouter, Depends, Header, File, Form, UploadFile
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import uuid
from datetime import datetime, timezone
import os
import asyncio

from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from . import schemas, repository, database, crypto_utils

app = FastAPI(title="Game Server Edge Platform - Center")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Center-Signature", "X-Center-Timestamp"]
)

api_router = APIRouter(prefix="/api")

# Initialize Database
@app.on_event("startup")
async def on_startup():
    crypto_utils.ensure_keys_exist()
    database.init_db()
    asyncio.create_task(s3_cleanup_loop())

async def s3_cleanup_loop():
    from .config import S3_ENABLED, UPLOAD_RETENTION_MINUTES
    from . import s3_utils
    
    if not S3_ENABLED:
        return
        
    print(f"Started S3 background cleanup loop (Retention: {UPLOAD_RETENTION_MINUTES}m)")
    while True:
        try:
            db_generator = database.get_db()
            db = next(db_generator)
            try:
                instances = repository.get_instances(db)
                running_instances = [i for i in instances if i.status == "RUNNING" and i.save_path and i.save_path.startswith("s3://")]
                
                for inst in running_instances:
                    last_modified = s3_utils.get_s3_file_last_modified(inst.save_path)
                    if last_modified:
                        # last_modified is a datetime object, usually timezone-aware from boto3
                        now = datetime.now(timezone.utc)
                        diff_minutes = (now - last_modified).total_seconds() / 60.0
                        
                        if diff_minutes > UPLOAD_RETENTION_MINUTES:
                            print(f"Instance {inst.id} S3 file is {diff_minutes:.1f}m old (>{UPLOAD_RETENTION_MINUTES}m). Deleting...")
                            s3_utils.delete_s3_file(inst.save_path)
            finally:
                db.close()
        except Exception as e:
            print(f"Error in S3 cleanup loop: {e}")
            
        await asyncio.sleep(300) # Run every 5 minutes

@api_router.get("/public_key")
async def get_public_key():
    return {"public_key": crypto_utils.get_public_key_pem()}

@api_router.post("/nodes/register", response_model=schemas.Node)
async def register_node(data: schemas.NodeRegister, db: Session = Depends(database.get_db)):
    if data.public_key:
        # Verify node_id matches public_key derivation
        from cryptography.hazmat.primitives import hashes, serialization
        import base64
        try:
            public_key_bytes = data.public_key.encode('utf-8')
            digest = hashes.Hash(hashes.SHA256())
            digest.update(public_key_bytes)
            fingerprint = digest.finalize()
            derived_id = base64.urlsafe_b64encode(fingerprint[:16]).decode('utf-8').rstrip('=')
            
            if data.node_id and data.node_id != derived_id:
                raise HTTPException(status_code=400, detail="Invalid node_id for provided public_key")
            data.node_id = derived_id
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid public_key format: {e}")

    db_node = repository.create_or_update_node(db, data)
    return db_node

@api_router.post("/nodes/{node_id}/heartbeat")
async def heartbeat(
    node_id: str, 
    payload: Dict = Body(...),
    x_signature: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None),
    db: Session = Depends(database.get_db)
):
    db_node = repository.get_node(db, node_id)
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Signature verification
    if db_node.public_key:
        if not x_signature:
            raise HTTPException(status_code=401, detail="Missing X-Signature header")
        
        # Verify signature
        is_valid, msg = crypto_utils.verify_signature(payload, x_signature, db_node.public_key)
        if not is_valid:
            raise HTTPException(status_code=401, detail=f"Signature verification failed: {msg}")

    load_avg = payload.get("load_avg", 0.0)
    running_instances = payload.get("running_instances", 0)
    resources = payload.get("resources")
    
    repository.update_node_heartbeat(db, node_id, load_avg, running_instances, resources)
    tasks = repository.get_pending_tasks(db, node_id)
    
    response_payload = {"status": "OK", "tasks": [{"type": t.type, "payload": t.payload} for t in tasks]}
    signature, timestamp = crypto_utils.sign_payload(response_payload)
    
    from fastapi.responses import JSONResponse
    return JSONResponse(
        content=response_payload,
        headers={
            "X-Center-Signature": signature,
            "X-Center-Timestamp": str(timestamp)
        }
    )

@api_router.post("/nodes/{node_id}/status")
async def update_node_status(
    node_id: str,
    payload: Dict = Body(...),
    x_signature: Optional[str] = Header(None),
    db: Session = Depends(database.get_db)
):
    db_node = repository.get_node(db, node_id)
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    if db_node.public_key:
        if not x_signature:
            raise HTTPException(status_code=401, detail="Missing X-Signature header")
        is_valid, msg = crypto_utils.verify_signature(payload, x_signature, db_node.public_key)
        if not is_valid:
            raise HTTPException(status_code=401, detail=f"Signature verification failed: {msg}")

    status = payload.get("status", "OFFLINE")
    repository.update_node_status(db, node_id, status)
    return {"status": "UPDATED"}

@api_router.post("/games/deploy")
def deploy_game(
    game_type: str = Form(...),
    owner_id: str = Form("local_user"),
    node_id: Optional[str] = Form(None),
    save_path: Optional[str] = Form(None),
    archive: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db)
):
    def can_deploy(n):
        max_instances = 3
        if n.resources and "max_game_instances" in n.resources:
            max_instances = int(n.resources["max_game_instances"])
        active_count = repository.get_active_instance_count(db, n.id)
        return active_count < max_instances, active_count

    if node_id:
        db_node = repository.get_node(db, node_id)
        if not db_node:
            raise HTTPException(status_code=404, detail="Selected node not found")
        if db_node.status != "ONLINE":
            raise HTTPException(status_code=503, detail="Selected node is not ONLINE")
            
        ok, _ = can_deploy(db_node)
        if not ok:
            raise HTTPException(status_code=400, detail="Selected node has reached max instance limit")
    else:
        nodes = repository.get_nodes(db)
        online_nodes = [n for n in nodes if n.status == "ONLINE"]
        available_nodes = []
        for n in online_nodes:
            ok, active_count = can_deploy(n)
            if ok:
                available_nodes.append((n, active_count))
                
        if not available_nodes:
            raise HTTPException(status_code=503, detail="No available nodes with capacity")
        
        # Sort available nodes by active_count to load balance
        available_nodes.sort(key=lambda x: x[1])
        target_node = available_nodes[0][0]
        node_id = target_node.id
    
    instance_id = str(uuid.uuid4())
    
    # S3 config loader
    try:
        from .config import S3_ENABLED, S3_BUCKET, S3_PATH_PREFIX
    except (ImportError, ValueError):
        S3_ENABLED, S3_BUCKET, S3_PATH_PREFIX = False, "game-saves", "instances"

    final_save_path = save_path
    
    # Process uploaded file if provided
    if archive and archive.filename:
        if not S3_ENABLED:
            raise HTTPException(status_code=400, detail="S3 is not enabled but archive was uploaded")
            
        temp_file_path = f"/tmp/{instance_id}_{archive.filename}"
        try:
            with open(temp_file_path, "wb") as buffer:
                import shutil
                shutil.copyfileobj(archive.file, buffer)
            
            s3_key = f"{S3_PATH_PREFIX}/{instance_id}.zip"
            from . import s3_utils
            success = s3_utils.upload_s3_raw_file(temp_file_path, s3_key)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to upload archive to S3")
                
            final_save_path = f"s3://{S3_BUCKET}/{s3_key}"
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    # Check default paths if no explicitly uploaded file or path
    elif not final_save_path:
        if S3_ENABLED:
            final_save_path = f"s3://{S3_BUCKET}/{S3_PATH_PREFIX}/{instance_id}.zip"
        else:
            final_save_path = f"local://tmp/game_saves/{instance_id}.zip"

    # Persist instance
    repository.create_instance(db, instance_id, node_id, game_type, owner_id, final_save_path)
    
    download_url = None
    if final_save_path and final_save_path.startswith("s3://"):
        from . import s3_utils
        download_url = s3_utils.generate_presigned_url(final_save_path, method="get_object")
        print(f"Generated download URL for DEPLOY task: {final_save_path}")

    # Queue task for agent
    task_payload = {
        "instance_id": instance_id,
        "game_type": game_type,
        "env": {"INSTANCE_ID": instance_id, "EULA": "TRUE"},
        "save_path": final_save_path,
        "download_url": download_url
    }
    repository.add_task(db, node_id, "DEPLOY", task_payload)
    
    return {"instance_id": instance_id, "node_id": node_id, "status": "QUEUED"}

@api_router.get("/instances/{instance_id}/backup_ticket")
def get_backup_ticket(instance_id: str, db: Session = Depends(database.get_db)):
    db_instance = repository.get_instance(db, instance_id)
    if not db_instance:
        raise HTTPException(status_code=404, detail="Instance not found")
        
    from .config import S3_ENABLED, S3_BUCKET
    if not S3_ENABLED:
        raise HTTPException(status_code=400, detail="S3 is disabled")
        
    remote_path = f"s3://{S3_BUCKET}/game_saved/{instance_id}.zip"
    from . import s3_utils
    upload_url = s3_utils.generate_presigned_url(remote_path, method="put_object", expires_in=3600)
    
    repository.update_instance_save_path(db, instance_id, remote_path)
    print(f"Issued backup ticket for {instance_id} -> {remote_path}")
    
    return {"upload_url": upload_url, "remote_path": remote_path}

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
