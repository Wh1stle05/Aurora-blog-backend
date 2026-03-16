from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Optional
import logging
import os
import uuid
import shutil
import base64

from ..deps import get_db, require_admin
from ..models import User, Post, Comment, Reaction, PostImage, UserNicknameHistory, UserEmailHistory, UserAvatarHistory, PostRevision
from .. import schemas

router = APIRouter(prefix="/api/admin", tags=["admin"])

UPLOAD_DIR = "uploads"

@router.get("/users/{user_id}/history/nickname", response_model=List[schemas.HistoryRead])
def get_user_nickname_history(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    histories = db.query(UserNicknameHistory).filter(UserNicknameHistory.user_id == user_id).order_by(UserNicknameHistory.created_at.desc()).all()
    return [schemas.HistoryRead(id=h.id, old_value=h.old_nickname, new_value=h.new_nickname, created_at=h.created_at) for h in histories]

@router.get("/users/{user_id}/history/email", response_model=List[schemas.HistoryRead])
def get_user_email_history(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    histories = db.query(UserEmailHistory).filter(UserEmailHistory.user_id == user_id).order_by(UserEmailHistory.created_at.desc()).all()
    return [schemas.HistoryRead(id=h.id, old_value=h.old_email, new_value=h.new_email, created_at=h.created_at) for h in histories]

@router.get("/users/{user_id}/history/avatar", response_model=List[schemas.HistoryRead])
def get_user_avatar_history(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    histories = db.query(UserAvatarHistory).filter(UserAvatarHistory.user_id == user_id).order_by(UserAvatarHistory.created_at.desc()).all()
    return [schemas.HistoryRead(id=h.id, old_value=h.old_avatar or "", new_value=h.new_avatar or "", created_at=h.created_at) for h in histories]

@router.post("/posts/upload-full")
async def upload_blog_post_full(
    md_file: UploadFile = File(...),
    images: List[UploadFile] = File([]),
    tags: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    上传整个博客：包含一个 .md 文件和多个可选的附件图片。
    图片将直接存储在数据库中，并与该博文关联。
    """
    # 1. 读取并处理 .md 文件
    if not md_file.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files are allowed")
    
    content_bytes = await md_file.read()
    content = content_bytes.decode("utf-8")
    
    # 简单从文件名或第一行获取标题
    title = md_file.filename.replace(".md", "")
    lines = content.split("\n")
    if lines and lines[0].startswith("# "):
        title = lines[0].replace("# ", "").strip()
        # 移除 Markdown 中的第一个一级标题以避免前端重复显示
        content = "\n".join(lines[1:])
    
    # 2. 创建博文记录
    new_post = Post(
        title=title,
        content=content,
        author_id=_admin.id,
        tags=tags # 使用传入的标签，而不是硬编码的 'uploaded'
    )
    db.add(new_post)
    db.flush() # 获取新生成的 post.id
    
    # 3. 处理并存储图片附件到数据库
    stored_images_info = []
    for img in images:
        if not img.content_type.startswith("image/"):
            continue
        
        img_data = await img.read()
        # 存储为 Base64 字符串（数据库友好且方便直接在前端 Data URI 中展示，尽管体积略大）
        b64_data = base64.b64encode(img_data).decode("utf-8")
        
        db_img = PostImage(
            post_id=new_post.id,
            filename=img.filename,
            content_type=img.content_type,
            data=b64_data
        )
        db.add(db_img)
        db.flush()
        
        stored_images_info.append({
            "id": db_img.id,
            "filename": img.filename,
            # 前端可以引用的伪路径，我们将会在渲染时拦截并替换
            "placeholder": f"{{{{IMAGE_{img.filename}}}}}"
        })
    
    db.commit()
    
    return {
        "ok": True, 
        "post_id": new_post.id,
        "title": title,
        "images_attached": len(stored_images_info),
        "attached_details": stored_images_info
    }

from ..utils.storage import save_file

@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    _admin: User = Depends(require_admin),
):
    # 检查是否是图片
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only images are allowed")
    
    # 使用统一存储工具保存图片
    try:
        url = await save_file(file, subfolder="posts")
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

@router.get("/users", response_model=List[schemas.AdminUserRead])
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    try:
        users = db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        user_ids = [u.id for u in users]
        
        post_counts = dict(
            db.query(Post.author_id, func.count(Post.id))
            .filter(Post.author_id.in_(user_ids))
            .group_by(Post.author_id)
            .all()
        ) if user_ids else {}
        
        comment_counts = dict(
            db.query(Comment.author_id, func.count(Comment.id))
            .filter(Comment.author_id.in_(user_ids))
            .group_by(Comment.author_id)
            .all()
        ) if user_ids else {}

        results = []
        for user in users:
            results.append(
                schemas.AdminUserRead(
                    id=user.id,
                    nickname=user.nickname,
                    email=user.email,
                    avatar=user.avatar,
                    created_at=user.created_at,
                    post_count=int(post_counts.get(user.id, 0)),
                    comment_count=int(comment_counts.get(user.id, 0)),
                    is_banned=getattr(user, "is_banned", 0),
                )
            )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/users/{user_id}/toggle_ban")
def toggle_user_ban(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email == _admin.email:
        raise HTTPException(status_code=400, detail="Cannot ban yourself")
    
    current_status = getattr(user, "is_banned", 0)
    user.is_banned = 0 if current_status == 1 else 1
    db.commit()
    return {"ok": True, "is_banned": user.is_banned}

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email == _admin.email:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # 软删除用户
    user.deleted_at = func.now()
    db.commit()
    return {"ok": True}


@router.get("/posts", response_model=List[schemas.PostRead])
def list_admin_posts(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|like_count|view_count)$"),
    show_deleted: bool = Query(False),
):
    from sqlalchemy import or_
    query = db.query(Post)
    
    if not show_deleted:
        query = query.filter(Post.deleted_at == None)
    else:
        query = query.filter(Post.deleted_at != None)
    
    if search:
        query = query.filter(or_(Post.title.contains(search), Post.content.contains(search)))
    
    if tag:
        # 简单处理：标签包含
        query = query.filter(Post.tags.contains(tag))

    if sort_by == "created_at":
        query = query.order_by(Post.created_at.desc())
    elif sort_by == "view_count":
        query = query.order_by(Post.view_count.desc())
    # like_count 排序稍复杂，目前暂不支持后端直接按聚合字段排，除非预存
    
    return query.offset(skip).limit(limit).all()

@router.post("/tags/{tag_id}/toggle_visibility")
def toggle_tag_visibility(
    tag_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    from ..models import Tag
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    tag.is_visible = 0 if tag.is_visible == 1 else 1
    db.commit()
    return {"ok": True, "is_visible": tag.is_visible}

@router.put("/posts/{post_id}", response_model=schemas.PostRead)
def update_admin_post(
    post_id: int,
    payload: schemas.PostUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # 在更新前，将当前内容存入历史版本
    if payload.content is not None and payload.content != post.content:
        revision = PostRevision(
            post_id=post.id,
            content=post.content,
            revision_note="Admin update"
        )
        db.add(revision)
    
    if payload.title is not None:
        post.title = payload.title
    if payload.content is not None:
        post.content = payload.content
    if payload.tags is not None:
        post.tags = payload.tags
    if payload.is_visible is not None:
        post.is_visible = payload.is_visible
        
    db.commit()
    db.refresh(post)
    return post

@router.delete("/posts/{post_id}")
def delete_admin_post(
    post_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # 软删除博文
    post.deleted_at = func.now()
    db.commit()
    return {"ok": True}

@router.post("/posts/{post_id}/restore")
def restore_admin_post(
    post_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post.deleted_at = None
    db.commit()
    return {"ok": True}

@router.get("/posts/{post_id}/revisions")
def get_post_revisions(
    post_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    revisions = db.query(PostRevision).filter(PostRevision.post_id == post_id).order_by(PostRevision.created_at.desc()).all()
    return revisions

@router.post("/revisions/{revision_id}/restore")
def restore_post_version(
    revision_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    revision = db.query(PostRevision).filter(PostRevision.id == revision_id).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")
    
    post = db.query(Post).filter(Post.id == revision.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # 恢复前先把当前内容存入历史
    current_rev = PostRevision(
        post_id=post.id,
        content=post.content,
        revision_note=f"Restored from version {revision_id}"
    )
    db.add(current_rev)
    
    post.content = revision.content
    db.commit()
    return {"ok": True}


@router.post("/system/cleanup-images")
def cleanup_orphaned_images(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """清理孤儿图片：删除未关联文章的数据库记录和物理文件"""
    # 1. 清理数据库记录：删除没有对应 Post 的 PostImage
    from ..models import Post
    orphans = db.query(PostImage).filter(~PostImage.post_id.in_(db.query(Post.id))).all()
    count_db = len(orphans)
    for orphan in orphans:
        db.delete(orphan)
    
    # 2. 清理物理文件：删除 uploads 文件夹中不在数据库记录里的文件
    files_in_dir = os.listdir(UPLOAD_DIR)
    db_filenames = [r[0] for r in db.query(PostImage.filename).all()]
    
    count_files = 0
    for f in files_in_dir:
        # 排除系统文件
        if f.startswith('.'): continue
        if f not in db_filenames:
            try:
                os.remove(os.path.join(UPLOAD_DIR, f))
                count_files += 1
            except: pass
            
    db.commit()
    return {"ok": True, "database_records_removed": count_db, "physical_files_removed": count_files}

@router.get("/comments", response_model=List[schemas.AdminCommentRead])
def list_comments(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        # 使用 explicit join 确保数据完整性
        rows = (
            db.query(Comment, Post)
            .join(Post, Comment.post_id == Post.id)
            .order_by(Comment.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        results = []
        for comment, post in rows:
            results.append(
                schemas.AdminCommentRead(
                    id=comment.id,
                    post_id=comment.post_id,
                    post_title=post.title,
                    author=schemas.UserRead.from_orm(comment.author),
                    content=comment.content,
                    created_at=comment.created_at,
                )
            )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comment fetch error: {str(e)}")


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # 软删除评论
    comment.deleted_at = func.now()
    db.commit()
    return {"ok": True}

@router.post("/comments/{comment_id}/toggle_visibility")
def toggle_comment_visibility(
    comment_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    comment.is_visible = 0 if comment.is_visible == 1 else 1
    db.commit()
    msg = "评论已隐藏" if comment.is_visible == 0 else "评论已恢复显示"
    return {"ok": True, "is_visible": comment.is_visible, "message": msg}
