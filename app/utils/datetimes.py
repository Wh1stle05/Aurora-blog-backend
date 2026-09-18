"""时间解析工具：把表单/JSON 传来的时间字符串统一转成带时区的 datetime。"""
from datetime import datetime, timezone


def to_utc(value: datetime) -> datetime:
    """无时区信息的时间按 UTC 处理（Vercel / Docker 默认都是 UTC）。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_optional_datetime(value: str | datetime | None) -> datetime | None:
    """解析可空时间。

    - None / 空字符串 -> None（表示「用默认值」，例如文章用上传时间）
    - 支持 ISO 8601，例如 2026-03-25T14:42:09Z / 2026-03-25T22:42 / 2026-03-25
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return to_utc(value)

    text = value.strip()
    if not text:
        return None

    if text.endswith(("Z", "z")):
        text = f"{text[:-1]}+00:00"

    try:
        return to_utc(datetime.fromisoformat(text))
    except ValueError as exc:
        raise ValueError(f"invalid datetime: {value!r}") from exc
