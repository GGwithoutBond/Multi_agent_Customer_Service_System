"""
文件上传 API
支持图片和文件上传，返回可访问的 URL
"""

import os
import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/upload", tags=["文件上传"])

# 允许的文件类型
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_FILE_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/csv",
}
ALL_ALLOWED = ALLOWED_IMAGE_TYPES | ALLOWED_FILE_TYPES

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_FILE_SIZE = 20 * 1024 * 1024   # 20 MB


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    """
    上传文件（图片或文档）
    返回文件的访问 URL 和元信息
    """
    # 1. 验证文件类型
    content_type = file.content_type or ""
    if content_type not in ALL_ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {content_type}。支持的类型: 图片(jpg/png/gif/webp), 文档(pdf/doc/xlsx/txt/csv)"
        )

    # 2. 读取文件内容
    content = await file.read()
    file_size = len(content)

    # 3. 验证文件大小
    is_image = content_type in ALLOWED_IMAGE_TYPES
    max_size = MAX_IMAGE_SIZE if is_image else MAX_FILE_SIZE
    if file_size > max_size:
        max_mb = max_size // (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制 ({max_mb}MB)"
        )

    # 4. 生成唯一文件名
    ext = os.path.splitext(file.filename or "file")[1] or ".bin"
    date_prefix = datetime.now().strftime("%Y%m%d")
    unique_name = f"{date_prefix}_{uuid.uuid4().hex[:12]}{ext}"

    # 5. 确定子目录
    sub_dir = "images" if is_image else "files"
    settings = get_settings()
    upload_base = os.path.join(settings.BASE_DIR if hasattr(settings, 'BASE_DIR') else ".", "uploads", sub_dir)
    os.makedirs(upload_base, exist_ok=True)

    # 6. 保存文件
    file_path = os.path.join(upload_base, unique_name)
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info("文件上传成功: %s (%d bytes)", unique_name, file_size)

    # 7. 返回结果
    file_url = f"/uploads/{sub_dir}/{unique_name}"
    file_type = "image" if is_image else "file"

    return {
        "url": file_url,
        "name": file.filename,
        "size": file_size,
        "type": file_type,
        "content_type": content_type,
    }
