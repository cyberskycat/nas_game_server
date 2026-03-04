import os
import base64
import json
import time
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# Path to local key files
PRIVATE_KEY_PATH = "/app/data/center.key"
PUBLIC_KEY_PATH = "/app/data/center_pub.pem"

def ensure_keys_exist():
    """保证密钥对存在，不存在则生成"""
    if not os.path.exists(PRIVATE_KEY_PATH):
        print("Generating new Ed25519 key pair...")
        private_key = ed25519.Ed25519PrivateKey.generate()
        
        # Save private key
        with open(PRIVATE_KEY_PATH, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.OpenSSH,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
        # Get and save public key
        public_key = private_key.public_key()
        with open(PUBLIC_KEY_PATH, "wb") as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        return True
    return False

def get_node_id_from_pubkey():
    """从公钥派生 Node ID（Base64 URL Safe）"""
    with open(PUBLIC_KEY_PATH, "rb") as f:
        public_key_bytes = f.read()
    
    # 使用 SHA256 摘要缩短 ID 长度，并进行 Base64 编码
    digest = hashes.Hash(hashes.SHA256())
    digest.update(public_key_bytes)
    fingerprint = digest.finalize()
    
    # 取前 16 字节并转为 Base64，作为可读 ID
    return base64.urlsafe_b64encode(fingerprint[:16]).decode('utf-8').rstrip('=')

def sign_payload(payload_dict):
    """使用私钥对负载进行签名，包含时间戳"""
    if "timestamp" not in payload_dict:
        payload_dict["timestamp"] = int(time.time())
    
    # 转换为有序 JSON 字符串保证签名一致性
    message = json.dumps(payload_dict, sort_keys=True).encode('utf-8')
    
    with open(PRIVATE_KEY_PATH, "rb") as f:
        private_key = serialization.load_ssh_private_key(f.read(), password=None)
        
    signature = private_key.sign(message)
    return base64.b64encode(signature).decode('utf-8'), payload_dict["timestamp"]

def get_public_key_pem():
    """返回公钥 PEM 字符串以便注册"""
    with open(PUBLIC_KEY_PATH, "rb") as f:
        return f.read().decode('utf-8')

# Center-side verification logic
def verify_signature(payload_dict, signature_b64, public_key_pem):
    """
    Center 端验证逻辑：
    1. 验证时间戳（防重放）
    2. 验证 Ed25519 签名
    """
    now = int(time.time())
    timestamp = payload_dict.get("timestamp", 0)
    
    # 允许 5 分钟内的时间偏差
    if abs(now - timestamp) > 300:
        return False, "Timestamp expired"
        
    try:
        signature = base64.b64decode(signature_b64)
        message = json.dumps(payload_dict, sort_keys=True).encode('utf-8')
        
        public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
        public_key.verify(signature, message)
        return True, "Valid"
    except Exception as e:
        return False, str(e)
