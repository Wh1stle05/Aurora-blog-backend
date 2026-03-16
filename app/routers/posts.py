from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_
from typing import List, Optional
import math
import base64

from ..deps import get_db, get_current_user, get_optional_current_user
from ..models import Post, Comment, Reaction, User, PostImage
from .. import schemas

router = APIRouter(prefix="/api/posts", tags=["posts"])

@router.get("/image/{image_id}")
async def get_post_image(image_id: int, db: Session = Depends(get_db)):
    """从数据库读取并返回二进制图片内容"""
    img = db.query(PostImage).filter(PostImage.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # 将 Base64 字符串解码回二进制
    try:
        binary_data = base64.b64decode(img.data)
        return Response(content=binary_data, media_type=img.content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to decode image data")

def _reaction_counts(db: Session, target_type: str, target_ids: list[int]) -> dict[int, dict[str, int]]:
    if not target_ids:
        return {}
    rows = (
        db.query(
            Reaction.target_id,
            func.sum(case((Reaction.value == 1, 1), else_=0)).label("likes"),
            func.sum(case((Reaction.value == -1, 1), else_=0)).label("dislikes"),
        )
        .filter(Reaction.target_type == target_type, Reaction.target_id.in_(target_ids))
        .group_by(Reaction.target_id)
        .all()
    )
    return {row.target_id: {"likes": int(row.likes or 0), "dislikes": int(row.dislikes or 0)} for row in rows}


@router.get("", response_model=List[schemas.PostRead])
def list_posts(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|likes|view_count)$"),
):
    query = db.query(Post)
    
    if search:
        query = query.filter(or_(Post.title.contains(search), Post.content.contains(search)))
    
    if tag:
        # Support multiple tags comma separated
        tags_list = tag.split(',')
        tag_filters = [Post.tags.contains(t.strip()) for t in tags_list]
        query = query.filter(or_(*tag_filters))

    if sort_by == "created_at":
        query = query.order_by(Post.created_at.desc())
    elif sort_by == "view_count":
        query = query.order_by(Post.view_count.desc())
    
    posts = query.offset(skip).limit(limit).all()
    post_ids = [p.id for p in posts]
    reaction_map = _reaction_counts(db, "post", post_ids)
    comment_counts = dict(
        db.query(Comment.post_id, func.count(Comment.id))
        .filter(Comment.post_id.in_(post_ids))
        .group_by(Comment.post_id)
        .all()
    ) if post_ids else {}

    results = []
    for post in posts:
        likes = reaction_map.get(post.id, {}).get("likes", 0)
        dislikes = reaction_map.get(post.id, {}).get("dislikes", 0)
        results.append(
            schemas.PostRead(
                id=post.id,
                title=post.title,
                content=post.content,
                tags=post.tags,
                view_count=post.view_count,
                created_at=post.created_at,
                author=post.author,
                like_count=likes,
                dislike_count=dislikes,
                comment_count=int(comment_counts.get(post.id, 0)),
            )
        )
    return results


@router.get("/paginated")
def list_posts_paginated(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(6, ge=1, le=50),
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|like_count|view_count)$"),
):
    # 基础查询：可见文章且未删除
    query = db.query(Post).filter(Post.is_visible == 1, Post.deleted_at == None)
    
    if search:
        query = query.filter(or_(Post.title.contains(search), Post.content.contains(search)))
    
    if tag:
        tags_list = [t.strip() for t in tag.split(',') if t.strip()]
        if tags_list:
            tag_filters = [Post.tags.contains(t) for t in tags_list]
            query = query.filter(or_(*tag_filters))

    # 如果按点赞数排序，需要进行聚合查询
    if sort_by == "like_count":
        # 使用子查询计算点赞数
        likes_subquery = (
            db.query(
                Reaction.target_id,
                func.count(Reaction.id).label("likes")
            )
            .filter(Reaction.target_type == "post", Reaction.value == 1)
            .group_by(Reaction.target_id)
            .subquery()
        )
        query = query.outerjoin(likes_subquery, Post.id == likes_subquery.c.target_id)
        query = query.order_by(func.coalesce(likes_subquery.c.likes, 0).desc(), Post.created_at.desc())
    elif sort_by == "view_count":
        query = query.order_by(Post.view_count.desc(), Post.created_at.desc())
    else:
        query = query.order_by(Post.created_at.desc())

    total = query.count()
    posts_subset = query.offset((page - 1) * page_size).limit(page_size).all()

    # 获取点赞/点踩/评论数（这里可以保留原来的批量获取逻辑，因为它是按当前页 ID 获取的，效率尚可）
    post_ids = [p.id for p in posts_subset]
    reaction_map = _reaction_counts(db, "post", post_ids)
    comment_counts = dict(
        db.query(Comment.post_id, func.count(Comment.id))
        .filter(Comment.post_id.in_(post_ids))
        .group_by(Comment.post_id)
        .all()
    ) if post_ids else {}

    data = []
    for post in posts_subset:
        like_count = reaction_map.get(post.id, {}).get("likes", 0)
        dislike_count = reaction_map.get(post.id, {}).get("dislikes", 0)
        data.append({
            "id": post.id,
            "title": post.title,
            "summary": post.content[:150] + "...",
            "tags": post.tags,
            "author": post.author.nickname,
            "created_at": post.created_at,
            "view_count": post.view_count,
            "like_count": like_count,
            "dislike_count": dislike_count,
            "comment_count": int(comment_counts.get(post.id, 0)),
        })
    
    return {
        "success": True,
        "data": {
            "data": data,
            "page": page,
            "total_pages": math.ceil(total / page_size) if total > 0 else 1,
            "total": total
        }
    }


@router.get("/{post_id}", response_model=schemas.PostRead)
def get_post(
    post_id: int, 
    skip_view: bool = Query(False),
    db: Session = Depends(get_db), 
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    post = db.query(Post).filter(Post.id == post_id, Post.deleted_at == None).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # 如果文章不可见，且当前用户不是管理员，返回 404
    from ..deps import ADMIN_EMAILS
    is_admin = current_user and current_user.email in ADMIN_EMAILS
    if post.is_visible == 0 and not is_admin:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if not skip_view:
        # Increment view count
        post.view_count += 1
        db.commit()
        db.refresh(post)
    
    reaction_map = _reaction_counts(db, "post", [post_id])
    comment_count = (
        db.query(func.count(Comment.id)).filter(Comment.post_id == post_id).scalar() or 0
    )
    
    user_reaction = 0
    if current_user:
        reaction = db.query(Reaction).filter(
            Reaction.user_id == current_user.id,
            Reaction.target_type == "post",
            Reaction.target_id == post_id
        ).first()
        if reaction:
            user_reaction = reaction.value

    return schemas.PostRead(
        id=post.id,
        title=post.title,
        content=post.content,
        tags=post.tags,
        view_count=post.view_count,
        created_at=post.created_at,
        author=post.author,
        like_count=reaction_map.get(post_id, {}).get("likes", 0),
        dislike_count=reaction_map.get(post_id, {}).get("dislikes", 0),
        comment_count=int(comment_count),
        user_reaction=user_reaction,
        images=post.images,
    )


@router.post("", response_model=schemas.PostRead)
def create_post(
    payload: schemas.PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = Post(
        title=payload.title, 
        content=payload.content, 
        tags=payload.tags,
        author_id=current_user.id
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return schemas.PostRead(
        id=post.id,
        title=post.title,
        content=post.content,
        tags=post.tags,
        view_count=0,
        created_at=post.created_at,
        author=post.author,
        like_count=0,
        dislike_count=0,
        comment_count=0,
    )


@router.put("/{post_id}", response_model=schemas.PostRead)
def update_post(
    post_id: int,
    payload: schemas.PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    if payload.title is not None:
        post.title = payload.title
    if payload.content is not None:
        post.content = payload.content
    if payload.tags is not None:
        post.tags = payload.tags
    db.commit()
    db.refresh(post)
    return get_post(post_id, db)


@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    
    # 软删除
    post.deleted_at = func.now()
    db.commit()
    return {"ok": True}
