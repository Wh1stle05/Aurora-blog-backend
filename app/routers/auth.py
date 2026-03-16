from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta, timezone
import random
import resend
import os

from .. import schemas
from ..models import User, VerificationCode, UserNicknameHistory, UserEmailHistory, UserAvatarHistory
from ..deps import get_db, get_current_user
from ..auth import hash_password, verify_password, create_access_token, JWT_EXPIRES_MINUTES

router = APIRouter(prefix="/api/auth", tags=["auth"])

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
resend.api_key = RESEND_API_KEY

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/send-code")
def send_verification_code(payload: schemas.SendCodeRequest, db: Session = Depends(get_db)):
    # 1. 频率限制：检查是否在 60s 内已发送过
    existing = db.query(VerificationCode).filter(VerificationCode.email == payload.email).first()
    if existing:
        # 假设 expires_at 是 10 分钟后，如果现在距离 expires_at 大于 9 分钟，说明是 1 分钟内刚发的
        # 更好的办法是存一个 created_at，但我们可以根据 expires_at 推算
        now = datetime.now(timezone.utc)
        time_passed = timedelta(minutes=10) - (existing.expires_at - now)
        if time_passed.total_seconds() < 60:
            raise HTTPException(status_code=429, detail="请稍后再试（60秒内仅限一次）")

    # 2. 生成 6 位数字验证码
    code = "".join([str(random.randint(0, 9)) for _ in range(6)])
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    # 3. 存储到数据库
    # 先删除该邮箱旧的验证码
    db.query(VerificationCode).filter(VerificationCode.email == payload.email).delete()
    
    db_code = VerificationCode(email=payload.email, code=code, expires_at=expires_at)
    db.add(db_code)
    db.commit()

    # 4. 调用 Resend 发送邮件
    print(f"\n[TEST MODE] 验证码已生成！\n邮箱: {payload.email}\n验证码: {code}\n请在终端日志中查看。\n")

    try:
        if RESEND_API_KEY and RESEND_API_KEY != "re_your_key_here":
            resend.Emails.send({
                "from": "Aurora Blog <onboarding@resend.dev>",
                "to": payload.email,
                "subject": f"【Aurora Blog】您的注册验证码：{code}",
                "html": f"""
                    <div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                        <h2 style="color: #3b82f6;">欢迎加入 Aurora Blog</h2>
                        <p>您正在注册账号，您的验证码为：</p>
                        <div style="font-size: 32px; font-weight: bold; color: #3b82f6; letter-spacing: 5px; margin: 20px 0;">
                            {code}
                        </div>
                        <p style="color: #666; font-size: 14px;">该验证码 10 分钟内有效。如果不是您本人操作，请忽略此邮件。</p>
                    </div>
                """
            })
        else:
            print("Skipping Resend email because API key is not configured.")
            
        return {"ok": True, "message": "验证码已发送（测试模式：请在服务器日志中查看）"}
    except Exception as e:
        print(f"Resend error: {e}")
        # 在测试模式下，即便邮件发送失败也返回成功，方便从日志中读取验证码
        return {"ok": True, "message": "邮件发送失败，但验证码已在日志中生成（测试模式）"}

@router.post("/register", response_model=schemas.UserRead)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    # 1. 校验验证码
    db_code = db.query(VerificationCode).filter(
        VerificationCode.email == payload.email,
        VerificationCode.code == payload.code
    ).first()

    now = datetime.now(timezone.utc)
    db_expires = db_code.expires_at if db_code else None
    if db_expires and db_expires.tzinfo is None:
        db_expires = db_expires.replace(tzinfo=timezone.utc)

    if not db_code or db_expires < now:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 2. 校验用户是否已存在
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    # 3. 创建用户
    user = User(
        nickname=payload.nickname,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    
    # 4. 注册成功后清理验证码
    db.query(VerificationCode).filter(VerificationCode.email == payload.email).delete()
    
    db.commit()
    db.refresh(user)
    return user

@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")
    
    token = create_access_token(str(user.id))
    
    # Set HttpOnly Cookie
    is_prod = os.getenv("ENV", "dev").lower() == "prod"
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=JWT_EXPIRES_MINUTES * 60,
        expires=JWT_EXPIRES_MINUTES * 60,
        samesite="lax" if not is_prod else "strict",
        secure=is_prod, # 生产环境下强制使用 HTTPS
    )
    
    return {
        "user": schemas.UserRead.model_validate(user),
        "access_token": token,
        "token_type": "bearer"
    }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token", httponly=True, samesite="lax")
    return {"ok": True}

@router.get("/me", response_model=schemas.UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user

from fastapi import UploadFile, File
import uuid
import shutil

from ..utils.storage import save_file

@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传并更新用户头像"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only images are allowed")
    
    # 使用统一存储工具保存头像
    try:
        new_avatar_url = await save_file(file, subfolder="avatars")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    # 记录历史
    old_avatar = current_user.avatar
    
    history = UserAvatarHistory(
        user_id=current_user.id,
        old_avatar=old_avatar,
        new_avatar=new_avatar_url
    )
    db.add(history)

    # 更新数据库
    current_user.avatar = new_avatar_url
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.put("/nickname", response_model=schemas.UserRead)
def update_nickname(
    payload: schemas.NicknameUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新昵称 (每周限改一次)"""
    now = datetime.now(timezone.utc)
    if current_user.last_nickname_at:
        # 兼容 naive/aware datetime
        last_change = current_user.last_nickname_at
        if last_change.tzinfo is None:
            last_change = last_change.replace(tzinfo=timezone.utc)
        
        if now - last_change < timedelta(days=7):
            delta = timedelta(days=7) - (now - last_change)
            hours = int(delta.total_seconds() // 3600)
            days = hours // 24
            msg = f"昵称每周只能修改一次。请在 {days}天 {hours % 24}小时 后再试。" if days > 0 else f"请在 {hours}小时 后再试。"
            raise HTTPException(status_code=400, detail=msg)

    old_nickname = current_user.nickname
    current_user.nickname = payload.nickname
    current_user.last_nickname_at = now
    
    # 记录历史
    history = UserNicknameHistory(
        user_id=current_user.id,
        old_nickname=old_nickname,
        new_nickname=payload.nickname
    )
    db.add(history)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.put("/email", response_model=schemas.UserRead)
def update_email(
    payload: schemas.EmailUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新邮箱 (需要验证码)"""
    # 1. 校验验证码
    db_code = db.query(VerificationCode).filter(
        VerificationCode.email == payload.email,
        VerificationCode.code == payload.code
    ).first()

    now = datetime.now(timezone.utc)
    db_expires = db_code.expires_at if db_code else None
    if db_expires and db_expires.tzinfo is None:
        db_expires = db_expires.replace(tzinfo=timezone.utc)

    if not db_code or db_expires < now:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 2. 校验新邮箱是否冲突
    if payload.email == current_user.email:
         raise HTTPException(status_code=400, detail="新邮箱不能与原邮箱相同")
         
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="该邮箱已被其他账号绑定")

    old_email = current_user.email
    current_user.email = payload.email
    
    # 记录历史
    history = UserEmailHistory(
        user_id=current_user.id,
        old_email=old_email,
        new_email=payload.email
    )
    db.add(history)
    
    # 清理验证码
    db.query(VerificationCode).filter(VerificationCode.email == payload.email).delete()
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/history/nickname", response_model=List[schemas.HistoryRead])
def get_nickname_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    histories = db.query(UserNicknameHistory).filter(UserNicknameHistory.user_id == current_user.id).order_by(UserNicknameHistory.created_at.desc()).all()
    return [schemas.HistoryRead(id=h.id, old_value=h.old_nickname, new_value=h.new_nickname, created_at=h.created_at) for h in histories]

@router.get("/history/email", response_model=List[schemas.HistoryRead])
def get_email_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    histories = db.query(UserEmailHistory).filter(UserEmailHistory.user_id == current_user.id).order_by(UserEmailHistory.created_at.desc()).all()
    return [schemas.HistoryRead(id=h.id, old_value=h.old_email, new_value=h.new_email, created_at=h.created_at) for h in histories]
