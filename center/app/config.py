import os

# S3 / MinIO Configuration
S3_ENABLED = os.getenv("S3_ENABLED", "True").lower() == "true"
S3_BUCKET = os.getenv("S3_BUCKET", "nasgamecenter")
S3_PATH_PREFIX = os.getenv("S3_PATH_PREFIX", "instances")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://192.168.1.77:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "GKecc03ce70894fe9c3f52d6bd")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "33b662a33c4c716eb33c3dce80d45790c1a26927575b578dc216990f37b10e32")
S3_REGION = os.getenv("S3_REGION", "garage")
S3_USE_SSL = os.getenv("S3_USE_SSL", "False").lower() == "true"
UPLOAD_RETENTION_MINUTES = int(os.getenv("UPLOAD_RETENTION_MINUTES", "30"))
