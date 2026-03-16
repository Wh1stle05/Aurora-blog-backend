import os
import uuid
import shutil
from fastapi import UploadFile
from vercel_blob.blob_store import put

UPLOAD_DIR = "uploads"

# 判断是否使用 Vercel Blob 存储
USE_BLOB = os.getenv("BLOB_READ_WRITE_TOKEN") is not None

async def save_file(file: UploadFile, subfolder: str = "") -> str:
    """
    保存上传的文件，并返回可访问的 URL。
    - 如果配置了 Vercel Blob，则上传至云端。
    - 否则，保存至本地 uploads 目录（适用于本地开发/Docker）。
    """
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    
    # 构造存储路径（云端或本地）
    store_path = f"{subfolder}/{filename}" if subfolder else filename
    
    if USE_BLOB:
        # Vercel Blob 模式
        file_content = await file.read()
        # 重置文件指针，以便后续可能的操作
        await file.seek(0)
        
        # 上传到 Vercel Blob
        # 注意：vercel_blob.put 会返回一个包含 url 的对象
        blob = put(store_path, file_content)
        return blob.get("url")
    else:
        # 本地存储模式 (Local/Docker)
        local_dir = os.path.join(UPLOAD_DIR, subfolder) if subfolder else UPLOAD_DIR
        os.makedirs(local_dir, exist_ok=True)
        
        local_path = os.path.join(local_dir, filename)
        
        with open(local_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 返回本地访问路径（需配合 FastAPI StaticFiles 挂载）
        return f"/uploads/{subfolder}/{filename}" if subfolder else f"/uploads/{filename}"

def delete_file(path: str):
    """
    删除文件逻辑（可选实现）。
    Vercel Blob 删除目前需要通过 SDK 指定 URL，本地则直接 os.remove。
    """
    if not USE_BLOB:
        # 本地模式才真正执行删除
        if path.startswith("/uploads/"):
            # 还原为本地物理路径
            local_path = path.replace("/uploads/", f"{UPLOAD_DIR}/", 1)
            if os.path.exists(local_path):
                os.remove(local_path)
