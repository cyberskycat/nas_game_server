from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

class NodeBase(BaseModel):
    hostname: str
    ip: str
    resources: Dict[str, float] = Field(..., example={"cpu_cores": 4, "ram_gb": 16})

class NodeRegister(NodeBase):
    node_id: str | None = None

class Node(NodeBase):
    id: str
    status: str
    last_seen: datetime
    running_instances: int
    load_avg: float

    class Config:
        from_attributes = True

class InstanceBase(BaseModel):
    game_type: str
    owner_id: str
    save_path: Optional[str] = None

class DeployRequest(InstanceBase):
    node_id: Optional[str] = None

class Instance(InstanceBase):
    id: str
    node_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    details: Optional[str] = None

    class Config:
        from_attributes = True

class Task(BaseModel):
    type: str # DEPLOY, STOP
    payload: Dict

    class Config:
        from_attributes = True
