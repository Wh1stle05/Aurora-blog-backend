import os
import uuid
import shutil
import boto3
from fastapi import UploadFile

UPLOAD_DIR = "uploads"

R2_ENDPOINT = os.getenv("R2_ENDPOINT")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_PUBLIC_BASE_URL = os.getenv("R2_PUBLIC_BASE_URL")
USE_R2 = all([R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_BASE_URL])


def _build_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )

async def save_file(file: UploadFile, subfolder: str = "", return_key: bool = False) -> str:
    """
    保存上传的文件，并返回可访问的 URL 或存储 key。
    - 如果配置了 R2，则上传至云端（公有桶）。
    - 否则，保存至本地 uploads 目录（适用于本地开发/Docker）。
    """
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    
    # 构造存储路径（云端或本地）
    store_path = f"{subfolder}/{filename}" if subfolder else filename
    
    if USE_R2:
        file_content = await file.read()
        await file.seek(0)
        client = _build_r2_client()
        client.put_object(
            Bucket=R2_BUCKET,
            Key=store_path,
            Body=file_content,
            ContentType=file.content_type or "application/octet-stream",
        )
        if return_key:
            return store_path
        return f"{R2_PUBLIC_BASE_URL.rstrip('/')}/{store_path}"
    else:
        # 本地存储模式 (Local/Docker)
        local_dir = os.path.join(UPLOAD_DIR, subfolder) if subfolder else UPLOAD_DIR
        os.makedirs(local_dir, exist_ok=True)
        
        local_path = os.path.join(local_dir, filename)
        
        with open(local_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        local_url = f"/uploads/{subfolder}/{filename}" if subfolder else f"/uploads/{filename}"
        return local_url if return_key else local_url

def delete_file(path: str):
    """
    删除文件逻辑（可选实现）。
    Vercel Blob 删除目前需要通过 SDK 指定 URL，本地则直接 os.remove。
    """
    if not USE_R2:
        if path.startswith("/uploads/"):
            local_path = path.replace("/uploads/", f"{UPLOAD_DIR}/", 1)
            if os.path.exists(local_path):
                os.remove(local_path)
