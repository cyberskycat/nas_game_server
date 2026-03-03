import time
import uuid
import socket
import requests
import psutil
import platform
import os
import json
import subprocess
import shutil
import zipfile
import threading
from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
import uvicorn

from . import database, repository

try:
    from .s3_utils import download_s3_zip, upload_s3_zip
except ImportError:
    try:
        from s3_utils import download_s3_zip, upload_s3_zip
    except ImportError:
        download_s3_zip = None
        upload_s3_zip = None

CENTER_URL = os.getenv("CENTER_URL", "http://localhost:8123")
NODE_ID_FILE = "/app/data/node_id.txt"
CURRENT_NODE_ID = None

app = FastAPI(title="Aurora Edge Agent")
api_router = APIRouter(prefix="/api")

# Mount local UI
ui_path = os.path.join(os.path.dirname(__file__), "ui_dist")
if os.path.exists(ui_path):
    app.mount("/ui", StaticFiles(directory=ui_path, html=True), name="ui")

def get_node_id():
    if os.path.exists(NODE_ID_FILE):
        with open(NODE_ID_FILE, "r") as f:
            return f.read().strip()
    return None

def save_node_id(node_id):
    with open(NODE_ID_FILE, "w") as f:
        f.write(node_id)

def get_system_stats():
    return {
        "cpu_cores": psutil.cpu_count(),
        "ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "ram_usage": psutil.virtual_memory().percent
    }

@api_router.get("/status")
async def get_status():
    stats = get_system_stats()
    db = database.get_db()
    try:
        instances = repository.get_local_instances(db)
        # Verify status with Docker
        local_instances = []
        for inst in instances:
            status = "UNKNOWN"
            uptime = "N/A"
            try:
                res = subprocess.run(["docker", "inspect", "-f", "{{.State.Status}}", f"game-{inst.instance_id}"], capture_output=True, text=True)
                if res.returncode == 0:
                    status = res.stdout.strip().upper()
                else:
                    status = "NOT_FOUND"
            except: pass
            
            local_instances.append({
                "id": inst.instance_id,
                "game_type": inst.game_type,
                "status": status,
                "uptime": uptime
            })
    finally:
        db.close()

    return {
        "node_id": CURRENT_NODE_ID,
        "load_avg": psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else 0.0,
        "ram_usage": stats["ram_usage"],
        "instances": local_instances
    }

app.include_router(api_router)

def register():
    node_id = get_node_id()
    hostname = socket.gethostname()
    # Try to get IP from environment variable first, fallback to socket
    ip = os.getenv("AGENT_IP")
    if not ip:
        try:
            ip = socket.gethostbyname(hostname)
        except:
            ip = "127.0.0.1"
            
    stats = get_system_stats()
    payload = {"hostname": hostname, "ip": ip, "resources": stats, "node_id": node_id}
    try:
        print(f"Registering node to {CENTER_URL} with IP: {ip}...")
        resp = requests.post(f"{CENTER_URL}/api/nodes/register", json=payload)
        resp.raise_for_status()
        data = resp.json()
        new_node_id = data["id"]
        if not node_id: save_node_id(new_node_id)
        return new_node_id
    except Exception as e:
        print(f"Registration failed: {e}")
        return None

def get_running_instances_count():
    try:
        result = subprocess.run(["docker", "ps", "--format", "{{.Names}}", "--filter", "status=running"], capture_output=True, text=True, check=True)
        names = result.stdout.strip().split("\n")
        return len([n for n in names if n.strip().startswith("game-")])
    except: return 0

def update_center_status(instance_id, status, details=None):
    try:
        payload = {"status": status}
        if details: payload["details"] = details
        requests.post(f"{CENTER_URL}/api/instances/{instance_id}/status", json=payload)
    except: pass

def sync_save(remote_path, local_path, direction="download"):
    print(f"sync_save: {direction} from {remote_path} to {local_path}")
    if not download_s3_zip:
        print("Error: s3_utils not imported correctly!")
        return False
    try:
        if remote_path.startswith("s3://"):
            if direction == "download": return download_s3_zip(remote_path, local_path)
            else: return upload_s3_zip(local_path, remote_path)
        elif remote_path.startswith("local://"):
            real_remote = remote_path.replace("local://", "/")
            if direction == "download":
                if os.path.exists(real_remote):
                    if os.path.exists(local_path): shutil.rmtree(local_path)
                    os.makedirs(local_path, exist_ok=True)
                    if real_remote.endswith(".zip"):
                        print(f"Extracting local zip {real_remote} to {local_path}...")
                        with zipfile.ZipFile(real_remote, 'r') as zip_ref: zip_ref.extractall(local_path)
                    else:
                        print(f"Copying local dir {real_remote} to {local_path}...")
                        shutil.copytree(real_remote, local_path, dirs_exist_ok=True)
                else: 
                    print(f"Local source {real_remote} not found, creating empty dir.")
                    os.makedirs(local_path, exist_ok=True)
            elif direction == "upload":
                dir_name = os.path.dirname(real_remote)
                if dir_name: os.makedirs(dir_name, exist_ok=True)
                if real_remote.endswith(".zip"):
                    print(f"Compressing {local_path} to {real_remote}...")
                    with zipfile.ZipFile(real_remote, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for root, dirs, files in os.walk(local_path):
                            for file in files: zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), local_path))
                else:
                    print(f"Copying {local_path} to {real_remote}...")
                    if os.path.exists(real_remote): shutil.rmtree(real_remote)
                    shutil.copytree(local_path, real_remote)
        return True
    except Exception as e:
        print(f"sync_save failed with error: {e}")
        return False

def find_minecraft_jar(volume_path):
    print(f"Searching for JAR in {volume_path}...")
    if not os.path.exists(volume_path): return None
    
    candidates = []
    for root, dirs, files in os.walk(volume_path):
        if "/libraries" in root or "\\libraries" in root:
            continue
        
        depth = root[len(volume_path):].count(os.sep)
        if depth > 3: continue 
        
        for f in files:
            if f.endswith(".jar"):
                full_path = os.path.join(root, f)
                try:
                    size = os.path.getsize(full_path)
                    if size < 5 * 1024 * 1024: continue 
                    
                    score = 0
                    name_lower = f.lower()
                    if "paper" in name_lower: score += 100
                    if "spigot" in name_lower: score += 80
                    if "purpur" in name_lower: score += 80
                    if "server" in name_lower: score += 50
                    
                    if score > 0:
                        print(f"Found candidate: {f} (Size: {size}, Depth: {depth}, Score: {score})")
                        candidates.append((score, size, full_path))
                except Exception as e:
                    print(f"Error checking {f}: {e}")
                    
    if not candidates:
        print("No server-like JARs found in scan.")
        return None
    
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best = candidates[0][2]
    print(f"Best candidate selected: {best}")
    return best

def download_default_jar(target_dir):
    jar_name = "paper-1.21.1-100.jar"
    url = f"https://api.papermc.io/v2/projects/paper/versions/1.21.1/builds/100/downloads/{jar_name}"
    print(f"Downloading default JAR: {jar_name}...")
    try:
        os.makedirs(target_dir, exist_ok=True)
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(os.path.join(target_dir, jar_name), "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192): f.write(chunk)
        return jar_name
    except: return None

def setup_minecraft_eula(local_volume):
    os.makedirs(local_volume, exist_ok=True)
    eula_path = os.path.join(local_volume, "eula.txt")
    if not os.path.exists(eula_path):
        with open(eula_path, "w") as f: f.write("eula=true\n")

def deploy_container(payload):
    global CURRENT_NODE_ID
    instance_id, game_type, env_vars, save_path = payload["instance_id"], payload["game_type"], payload.get("env", {}), payload.get("save_path", "")
    
    # Persist locally first
    db = database.get_db()
    repository.create_or_update_instance(db, instance_id, game_type, "PROVISIONING", save_path)
    db.close()

    image = "eclipse-temurin:21-jre-jammy" if game_type == "minecraft" else "nginx:alpine"
    local_volume = f"/tmp/edge_agent_data/{CURRENT_NODE_ID}/{instance_id}"
    if save_path:
        if not sync_save(save_path, local_volume, "download"):
            update_center_status(instance_id, "FAILED", details="S3 backup sync failed")
            return False
    
    jar_file = None
    if game_type == "minecraft":
        setup_minecraft_eula(local_volume)
        jar_file = find_minecraft_jar(local_volume)
        if not jar_file:
            print("No JAR found in backup, downloading default...")
            jar_name = download_default_jar(local_volume)
            if jar_name: jar_file = os.path.join(local_volume, jar_name)
        
        if not jar_file:
            update_center_status(instance_id, "FAILED", details="No Minecraft JAR found or downloaded")
            return False
            
        rel_jar_path = os.path.relpath(jar_file, local_volume)
        print(f"Using JAR: {rel_jar_path}")

    cmd = ["docker", "run", "-d", "--name", f"game-{instance_id}"]
    if game_type == "minecraft": cmd.extend(["-p", "25565", "--workdir", "/data"])
    for k, v in env_vars.items(): cmd.extend(["-e", f"{k}={v}"])
    if save_path: cmd.extend(["-v", f"{local_volume}:/data"])
    cmd.append(image)
    if game_type == "minecraft": cmd.extend(["java", "-Xmx4G", "-Xms1G", "-jar", rel_jar_path, "--nogui"])
    
    try:
        subprocess.run(cmd, check=True)
        # Fetch the dynamically allocated host port
        port_details = ""
        try:
            p_res = subprocess.run(["docker", "port", f"game-{instance_id}", "25565"], capture_output=True, text=True)
            if p_res.returncode == 0 and p_res.stdout.strip():
                mapped_port = p_res.stdout.strip().split("\n")[0].split(":")[-1]
                port_details = f"Minecraft Port: {mapped_port}"
        except: pass
        
        db = database.get_db()
        repository.create_or_update_instance(db, instance_id, game_type, "RUNNING", save_path)
        db.close()
        update_center_status(instance_id, "RUNNING", details=port_details)
        return True
    except:
        update_center_status(instance_id, "FAILED")
        return False

def stop_container(payload):
    instance_id, save_path = payload["instance_id"], payload.get("save_path", "")
    container_name, local_volume = f"game-{instance_id}", f"/tmp/edge_agent_data/{CURRENT_NODE_ID}/{instance_id}"
    try:
        subprocess.run(["docker", "stop", container_name], check=False)
        subprocess.run(["docker", "rm", container_name], check=False)
        if save_path: sync_save(save_path, local_volume, "upload")
        
        # Remove from local DB or update status
        db = database.get_db()
        repository.remove_instance(db, instance_id)
        db.close()
        
        update_center_status(instance_id, "STOPPED")
        return True
    except: return False

def handle_tasks(tasks):
    if not tasks: return
    print(f"Received {len(tasks)} tasks: {tasks}")
    for task in tasks:
        task_type = task.get("type")
        payload = task.get("payload")
        print(f"Dispatching task {task_type} in new thread...")
        
        def run_task(tt, p):
            try:
                if tt == "DEPLOY": deploy_container(p)
                elif tt == "STOP": stop_container(p)
                else: print(f"Unknown task type: {tt}")
            except Exception as e:
                print(f"Task {tt} failed with error: {e}")

        t = threading.Thread(target=run_task, args=(task_type, payload))
        t.daemon = True
        t.start()

def heartbeat_loop():
    global CURRENT_NODE_ID
    while True:
        try:
            if not CURRENT_NODE_ID: 
                CURRENT_NODE_ID = register()
                print(f"Registered with Node ID: {CURRENT_NODE_ID}")
            
            if CURRENT_NODE_ID:
                resp = requests.post(
                    f"{CENTER_URL}/api/nodes/{CURRENT_NODE_ID}/heartbeat", 
                    json={
                        "load_avg": psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else 0.0, 
                        "running_instances": get_running_instances_count()
                    },
                    timeout=5
                )
                if resp.status_code == 404: 
                    print("Node ID not found on Center, re-registering...")
                    CURRENT_NODE_ID = register()
                else:
                    data = resp.json()
                    tasks = data.get("tasks", [])
                    handle_tasks(tasks)
        except Exception as e: 
            print(f"Heartbeat error: {e}")
        time.sleep(5)

import signal
import sys

def shutdown_handler(sig, frame):
    global CURRENT_NODE_ID
    print(f"\nShutdown signal {sig} received. Notifying Center...")
    if CURRENT_NODE_ID:
        try:
            requests.post(
                f"{CENTER_URL}/api/nodes/{CURRENT_NODE_ID}/status", 
                json={"status": "OFFLINE"},
                timeout=2
            )
            print("Center notified: OFFLINE")
        except:
            print("Failed to notify Center of shutdown.")
    sys.exit(0)

@app.on_event("startup")
def startup_event():
    database.init_db()
    # Register signal handlers
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    threading.Thread(target=heartbeat_loop, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run("edge_agent.agent:app", host="0.0.0.0", port=8001)
