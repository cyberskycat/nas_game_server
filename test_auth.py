import requests, time, json
from edge_agent.crypto_utils import sign_payload, verify_signature

payload = {"load_avg": 0.0, "running_instances": 0, "resources": {}, "timestamp": int(time.time())}
sig, ts = sign_payload(payload)

r = requests.post("http://center:8123/api/nodes/GYHVtanaAEMEdnLGT46lqw/heartbeat", json=payload, headers={"X-Signature": sig, "X-Timestamp": str(ts)})
center_sig = r.headers.get("x-center-signature")
data = r.json()

with open("/app/data/center_pub.pem", "r") as f:
    center_pub = f.read()

is_valid, msg = verify_signature(data, center_sig, center_pub)
print("Center sig:", center_sig[:20] + "...")
print("Data:", data)
print("Valid:", is_valid, "Msg:", msg)
