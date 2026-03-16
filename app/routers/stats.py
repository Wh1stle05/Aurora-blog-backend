from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..deps import get_db
from ..models import Post, Comment, Reaction

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("")
def get_stats(db: Session = Depends(get_db)):
    # 仅统计可见博文
    visible_posts_query = db.query(Post.id).filter(Post.is_visible == 1)
    
    post_count = visible_posts_query.count()
    total_views = db.query(func.sum(Post.view_count)).filter(Post.is_visible == 1).scalar() or 0
    
    # 仅统计可见博文下的评论
    comment_count = db.query(func.count(Comment.id)).filter(Comment.post_id.in_(visible_posts_query)).scalar() or 0
    
    # 仅统计可见博文的点赞
    total_likes = db.query(func.count(Reaction.id))\
        .filter(Reaction.target_type == 'post')\
        .filter(Reaction.target_id.in_(visible_posts_query))\
        .filter(Reaction.value == 1).scalar() or 0
    
    return {
        "success": True,
        "data": {
            "posts": post_count,
            "views": total_views,
            "comments": comment_count,
            "likes": total_likes
        }
    }
