from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Dict, Optional

from app.api.deps import get_db, get_current_user, get_optional_current_user
from app.models import Comment, Post, Reaction, User
from app import schemas

router = APIRouter(prefix="/api/posts", tags=["comments"])


def _comment_reaction_counts(db: Session, comment_ids: list[int]) -> dict[int, dict[str, int]]:
    if not comment_ids:
        return {}
    rows = (
        db.query(
            Reaction.target_id,
            func.sum(case((Reaction.value == 1, 1), else_=0)).label("likes"),
            func.sum(case((Reaction.value == -1, 1), else_=0)).label("dislikes"),
        )
        .filter(Reaction.target_type == "comment", Reaction.target_id.in_(comment_ids))
        .group_by(Reaction.target_id)
        .all()
    )
    return {row.target_id: {"likes": int(row.likes or 0), "dislikes": int(row.dislikes or 0)} for row in rows}


def _build_tree(
    comments: list[Comment],
    counts: dict[int, dict[str, int]],
    user_reactions: dict[int, int],
    content_overrides: Optional[dict[int, str]] = None,
) -> List[schemas.CommentRead]:
    by_id: Dict[int, schemas.CommentRead] = {}
    roots: List[schemas.CommentRead] = []
    overrides = content_overrides or {}

    for c in comments:
        count = counts.get(c.id, {})
        by_id[c.id] = schemas.CommentRead(
            id=c.id,
            post_id=c.post_id,
            author=c.author,
            parent_id=c.parent_id,
            content=overrides.get(c.id, c.content),
            is_visible=c.is_visible,
            created_at=c.created_at,
            like_count=count.get("likes", 0),
            dislike_count=count.get("dislikes", 0),
            user_reaction=user_reactions.get(c.id, 0),
            children=[],
        )

    for c in comments:
        node = by_id[c.id]
        if c.parent_id and c.parent_id in by_id:
            by_id[c.parent_id].children.append(node)
        else:
            roots.append(node)

    return roots


def _filter_public_comments(comments: list[Comment]) -> list[Comment]:
    by_id = {c.id: c for c in comments}
    deleted_ids = {
        c.id for c in comments if c.is_visible == -1 or c.deleted_at is not None
    }
    if not deleted_ids:
        return comments

    def has_deleted_ancestor(comment: Comment) -> bool:
        parent_id = comment.parent_id
        while parent_id:
            if parent_id in deleted_ids:
                return True
            parent = by_id.get(parent_id)
            if not parent:
                break
            parent_id = parent.parent_id
        return False

    return [
        c
        for c in comments
        if c.id not in deleted_ids and not has_deleted_ancestor(c)
    ]


@router.get("/{post_id}/comments", response_model=List[schemas.CommentRead])
def list_comments(post_id: int, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_optional_current_user)):
    post = db.query(Post).filter(Post.id == post_id, Post.deleted_at == None).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # 基础查询：该文章下的所有评论
    query = db.query(Comment).filter(Comment.post_id == post_id)
    
    # 如果是管理员，可以显示所有评论（包括不可见的和软删除的）来方便管理
    from app.api.deps import ADMIN_EMAILS
    is_admin = current_user and current_user.email in ADMIN_EMAILS

    comments = query.order_by(Comment.created_at.asc()).all()
    content_overrides = None
    if not is_admin:
        comments = _filter_public_comments(comments)
        content_overrides = {c.id: "" for c in comments if c.is_visible == 0}

    comment_ids = [c.id for c in comments]
    counts = _comment_reaction_counts(db, comment_ids)
    
    user_reactions = {}
    if current_user and comment_ids:
        user_reaction_rows = db.query(Reaction).filter(
            Reaction.user_id == current_user.id,
            Reaction.target_type == "comment",
            Reaction.target_id.in_(comment_ids)
        ).all()
        for r in user_reaction_rows:
            user_reactions[r.target_id] = r.value

    return _build_tree(comments, counts, user_reactions, content_overrides)


@router.delete("/comments/{comment_id}")
def user_delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户软删除自己的评论"""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # 权限校验：只能删除自己的
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own comments")
    
    # 软删除
    comment.is_visible = -1
    comment.deleted_at = func.now()
    db.commit()
    return {"ok": True, "message": "Comment hidden by user"}


@router.post("/{post_id}/comments", response_model=schemas.CommentRead)
def create_comment(
    post_id: int,
    payload: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if getattr(current_user, "is_banned", 0) == 1:
        raise HTTPException(status_code=403, detail="You have been banned from commenting")

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if payload.parent_id:
        parent = db.query(Comment).filter(Comment.id == payload.parent_id, Comment.post_id == post_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Parent comment not found")

    comment = Comment(
        post_id=post_id,
        author_id=current_user.id,
        parent_id=payload.parent_id,
        content=payload.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return schemas.CommentRead(
        id=comment.id,
        post_id=comment.post_id,
        author=comment.author,
        parent_id=comment.parent_id,
        content=comment.content,
        created_at=comment.created_at,
        like_count=0,
        dislike_count=0,
        children=[],
    )
