import os
import uuid
import boto3
from fastapi import UploadFile

R2_ENDPOINT = os.getenv("R2_ENDPOINT")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_PUBLIC_BASE_URL = os.getenv("R2_PUBLIC_BASE_URL")
USE_R2 = all([R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_BASE_URL])

if not USE_R2:
    raise RuntimeError("R2 configuration is required in this environment")


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
    - 上传至 R2（公有桶）。
    """
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    
    # 构造存储路径（云端）
    store_path = f"{subfolder}/{filename}" if subfolder else filename
    
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

def delete_file(path: str):
    """
    删除文件逻辑（可选实现）。
    Vercel Blob 删除目前需要通过 SDK 指定 URL。
    """
    return None
