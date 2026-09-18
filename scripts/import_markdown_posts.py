#!/usr/bin/env python
"""把本地 Markdown 文件批量导入博客数据库（posts / post_images / tags / users）。

用途：从旧服务器/本地备份恢复文章，或把一批 .md 一次性灌进新库。

示例：

    # 1) 先干跑，看看会插哪些文章（不会写库）
    python scripts/import_markdown_posts.py --manifest import.json --dry-run

    # 2) 真跑（数据库连接串可用 DATABASE_URL / POSTGRES_URL，或 --database-url 指定）
    DATABASE_URL="postgresql://..." python scripts/import_markdown_posts.py --manifest import.json

manifest.json 结构：

{
  "author": {"email": "you@example.com", "nickname": "Wh1stle", "password": "仅作者不存在时用于创建账号"},
  "posts": [
    {
      "path": "D:/博客/xxx.md",            // 必填
      "title": "标题",                      // 可选，默认取第一行 "# 标题" 或文件名
      "slug": "自定义-slug",                // 可选，默认按标题生成并去重
      "tags": ["linux", "docker"],          // 可选
      "created_at": "2026-03-25T14:42:09Z", // 可选，默认使用文件 mtime（= 上传时间）
      "published_at": null,                 // 可选，页面展示时间；留空/null 表示跟随上传时间
      "view_count": 0,                      // 可选
      "summary": "摘要",                    // 可选，默认自动抽取正文前 160 字
      "cover_image": null,                  // 可选
      "replace": {"./a.png": "https://cdn.example.com/posts/a.png"},  // 可选，正文里的字符串替换
      "images": [                            // 可选，登记附件（不会真的上传文件，只写关联记录）
        {"filename": "a.png", "object_key": "posts/xxx.png", "content_type": "image/png"}
      ]
    }
  ]
}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", required=True, help="manifest JSON 路径")
    parser.add_argument("--database-url", default=None, help="覆盖 DATABASE_URL / POSTGRES_URL")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不写数据库")
    parser.add_argument("--update-existing", action="store_true", help="slug 已存在时更新而不是跳过")
    return parser.parse_args()


def load_markdown(path: Path) -> tuple[str, str]:
    """返回 (title_from_h1_or_empty, content_without_h1)。"""
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    text = raw.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    lines = text.split("\n")
    if lines and lines[0].startswith("# "):
        return lines[0][2:].strip(), "\n".join(lines[1:]).strip("\n")
    return "", text


def main() -> int:
    args = parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    if not (os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")):
        print("错误：需要 DATABASE_URL / POSTGRES_URL，或用 --database-url 指定", file=sys.stderr)
        return 2

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    from sqlalchemy import select

    from app.core.security import hash_password
    from app.db.session import SessionLocal
    from app.models import Post, PostImage, Tag, User
    from app.services.slugs import build_summary, generate_unique_slug
    from app.utils.datetimes import parse_optional_datetime

    author_conf = manifest.get("author") or {}
    author_email = (author_conf.get("email") or "").strip()
    if not author_email:
        print("错误：manifest.author.email 必填", file=sys.stderr)
        return 2

    created_slugs: list[str] = []
    updated_slugs: list[str] = []
    skipped_slugs: list[str] = []

    with SessionLocal() as db:
        author = db.query(User).filter(User.email == author_email).first()
        if author is None:
            password = author_conf.get("password")
            if not password:
                print(f"错误：作者 {author_email} 不存在，且 manifest.author.password 为空", file=sys.stderr)
                return 2
            author = User(
                nickname=author_conf.get("nickname") or author_email.split("@")[0],
                email=author_email,
                password_hash=hash_password(password),
            )
            print(f"[author] 新建作者 {author_email}（昵称 {author.nickname}）")
            if not args.dry_run:
                db.add(author)
                db.flush()
        else:
            print(f"[author] 使用已有作者 {author_email}（id={author.id}）")

        for entry in manifest.get("posts", []):
            path = Path(entry["path"])
            if not path.is_file():
                print(f"[skip] 文件不存在：{path}", file=sys.stderr)
                continue

            h1_title, content = load_markdown(path)
            title = (entry.get("title") or h1_title or path.stem).strip()

            for old, new in (entry.get("replace") or {}).items():
                content = content.replace(old, new)

            created_at = parse_optional_datetime(entry.get("created_at"))
            if created_at is None:
                created_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            published_at = parse_optional_datetime(entry.get("published_at"))
            tags = entry.get("tags") or []
            summary = entry.get("summary") or build_summary(content)

            existing = None
            if entry.get("slug"):
                existing = db.query(Post).filter(Post.slug == entry["slug"]).first()

            if existing is not None and not args.update_existing:
                skipped_slugs.append(existing.slug)
                print(f"[skip] slug 已存在：{existing.slug}（{title}）")
                continue

            if existing is not None:
                existing.title = title
                existing.content = content
                existing.summary = summary
                existing.tags = ",".join(tags) if tags else None
                existing.created_at = created_at
                existing.published_at = published_at
                if entry.get("view_count") is not None:
                    existing.view_count = int(entry["view_count"])
                post = existing
                updated_slugs.append(post.slug)
                print(f"[update] {post.slug}  ← {path.name}")
            else:
                slug = generate_unique_slug(db, title=title, preferred_slug=entry.get("slug"))
                post = Post(
                    title=title,
                    slug=slug,
                    content=content,
                    summary=summary,
                    cover_image=entry.get("cover_image"),
                    tags=",".join(tags) if tags else None,
                    view_count=int(entry.get("view_count") or 0),
                    is_visible=1,
                    author_id=author.id,
                    created_at=created_at,
                    published_at=published_at,
                )
                print(
                    f"[create] {slug}  ← {path.name}  "
                    f"(上传时间 {created_at:%Y-%m-%d %H:%M} UTC, "
                    f"展示时间 {(published_at or created_at):%Y-%m-%d %H:%M} UTC, "
                    f"标签 {tags or '无'})"
                )
                if not args.dry_run:
                    db.add(post)
                    db.flush()
                created_slugs.append(slug)

            # 登记附件图片（只写数据库关联，文件本身需要已经在 R2 上）
            for img in entry.get("images") or []:
                filename = img.get("filename")
                object_key = img.get("object_key")
                if not filename or not object_key:
                    continue
                if args.dry_run:
                    print(f"         + 图片 {filename} -> {object_key}")
                    continue
                exists = (
                    db.execute(
                        select(PostImage).where(
                            PostImage.post_id == post.id,
                            PostImage.object_key == object_key,
                        )
                    ).first()
                    is not None
                )
                if exists:
                    continue
                db.add(
                    PostImage(
                        post_id=post.id,
                        filename=filename,
                        content_type=img.get("content_type") or "image/png",
                        object_key=object_key,
                    )
                )

            # 保证标签表里有这些标签（后台标签管理会用）
            for tag_name in tags:
                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                if tag is None and not args.dry_run:
                    db.add(Tag(name=tag_name))

        if args.dry_run:
            db.rollback()
            print("\n[dry-run] 未写入数据库")
        else:
            db.commit()
            print(
                f"\n完成：新建 {len(created_slugs)} 篇，更新 {len(updated_slugs)} 篇，"
                f"跳过 {len(skipped_slugs)} 篇"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
