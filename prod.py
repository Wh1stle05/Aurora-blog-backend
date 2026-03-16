import uvicorn
import os
import multiprocessing

# 生产环境入口脚本
# 使用方式: python prod.py

if __name__ == "__main__":
    # 动态获取 CPU 核心数，通常建议是 (2 x cores) + 1
    cores = multiprocessing.cpu_count()
    workers = int(os.getenv("WORKERS", cores * 2 + 1))
    port = int(os.getenv("PORT", 8000))
    
    print(f"Starting production server on port {port} with {workers} workers...")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        workers=workers,
        proxy_headers=True,
        forwarded_allow_ips="*",
        log_level="info",
        access_log=False # 生产环境建议关闭 access_log 或通过 Nginx 处理，提升性能
    )
