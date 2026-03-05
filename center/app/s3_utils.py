import boto3
import os
import zipfile
import shutil
from botocore.client import Config
try:
    from .config import S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET, S3_REGION, S3_USE_SSL
except ImportError:
    from config import S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET, S3_REGION, S3_USE_SSL

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        use_ssl=S3_USE_SSL,
        config=Config(signature_version='s3v4')
    )

def download_s3_zip(remote_path, local_extract_path):
    """
    从 S3 下载 ZIP 并解压到本地目录
    """
    s3 = get_s3_client()
    bucket = S3_BUCKET
    key = remote_path
    if remote_path.startswith("s3://"):
        parts = remote_path.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1]
    
    tmp_zip = f"{local_extract_path}.tmp.zip"
    os.makedirs(os.path.dirname(tmp_zip), exist_ok=True)
    
    try:
        print(f"Downloading from S3: {bucket}/{key} -> {tmp_zip}")
        s3.download_file(bucket, key, tmp_zip)
        
        # 解压
        if os.path.exists(local_extract_path):
            shutil.rmtree(local_extract_path)
        os.makedirs(local_extract_path, exist_ok=True)
        
        with zipfile.ZipFile(tmp_zip, 'r') as zip_ref:
            zip_ref.extractall(local_extract_path)
        
        os.remove(tmp_zip)
        print("S3 download and extraction complete.")
        return True
    except Exception as e:
        print(f"S3 download failed: {e}")
        if os.path.exists(tmp_zip):
            os.remove(tmp_zip)
        return False

def upload_s3_zip(local_path, remote_path):
    """
    将本地目录打包成 ZIP 并上传到 S3
    """
    s3 = get_s3_client()
    bucket = S3_BUCKET
    key = remote_path
    if remote_path.startswith("s3://"):
        parts = remote_path.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1]

    if not os.path.exists(local_path):
        print(f"Local path {local_path} does not exist, skipping upload.")
        return False

    tmp_zip = f"{local_path}.upload.zip"
    try:
        print(f"Archiving {local_path} to {tmp_zip}...")
        
        with zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(local_path):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), local_path)
                    zipf.write(os.path.join(root, file), rel_path)
                    
        print(f"Uploading to S3: {tmp_zip} -> {bucket}/{key}")
        s3.upload_file(tmp_zip, bucket, key)
        os.remove(tmp_zip)
        print("S3 upload complete.")
        return True
    except Exception as e:
        print(f"S3 upload failed: {e}")
        if os.path.exists(tmp_zip):
            os.remove(tmp_zip)
        return False

def upload_s3_raw_file(local_file_path, remote_path):
    """
    直接将本地文件上传到 S3
    """
    s3 = get_s3_client()
    bucket = S3_BUCKET
    key = remote_path
    if remote_path.startswith("s3://"):
        parts = remote_path.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1]

    if not os.path.exists(local_file_path):
        print(f"Local file {local_file_path} does not exist, skipping upload.")
        return False

    try:
        print(f"Uploading file to S3: {local_file_path} -> {bucket}/{key}")
        s3.upload_file(local_file_path, bucket, key)
        print("S3 file upload complete.")
        return True
    except Exception as e:
        print(f"S3 file upload failed: {e}")
        return False

def get_s3_file_last_modified(remote_path):
    """
    获取S3文件的最后修改时间
    """
    s3 = get_s3_client()
    bucket = S3_BUCKET
    key = remote_path
    if remote_path.startswith("s3://"):
        parts = remote_path.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1]

    try:
        response = s3.head_object(Bucket=bucket, Key=key)
        return response['LastModified']
    except Exception as e:
        print(f"Failed to get S3 file metadata for {remote_path}: {e}")
        return None

def delete_s3_file(remote_path):
    """
    删除S3文件
    """
    s3 = get_s3_client()
    bucket = S3_BUCKET
    key = remote_path
    if remote_path.startswith("s3://"):
        parts = remote_path.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1]

    try:
        s3.delete_object(Bucket=bucket, Key=key)
        print(f"Deleted S3 file: {remote_path}")
        return True
    except Exception as e:
        print(f"Failed to delete S3 file {remote_path}: {e}")
        return False

def generate_presigned_url(remote_path, method="get_object", expires_in=3600):
    """
    生成 S3 预签名 URL
    method: 'get_object' 或 'put_object'
    """
    s3 = get_s3_client()
    bucket = S3_BUCKET
    key = remote_path
    if remote_path.startswith("s3://"):
        parts = remote_path.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1]

    try:
        url = s3.generate_presigned_url(
            ClientMethod=method,
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expires_in
        )
        return url
    except Exception as e:
        print(f"Failed to generate presigned URL for {remote_path}: {e}")
        return None
