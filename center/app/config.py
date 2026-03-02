import os

# S3 / MinIO Configuration
S3_ENABLED = os.getenv("S3_ENABLED", "True").lower() == "true"
S3_BUCKET = os.getenv("S3_BUCKET", "nasgamecenter")
S3_PATH_PREFIX = os.getenv("S3_PATH_PREFIX", "instances")
