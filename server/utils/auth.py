# -*- coding: utf-8 -*-
"""
登录鉴权工具

采用 JWT（JSON Web Token）实现无状态登录：
  1. 登录成功后服务端签发一个加密的 Token 返回给前端
  2. 前端把 Token 保存到 localStorage，之后每次请求放到请求头 Authorization 中
  3. 服务端在处理请求前解析 Token，得到当前登录用户

请求头格式：Authorization: Bearer xxxxx.yyyyy.zzzzz
"""
import functools
from datetime import datetime, timedelta

import jwt
from flask import current_app, g, request

from models import SysUser, db
from utils.response import CODE_FORBIDDEN, CODE_UNAUTHORIZED, error


def create_token(user: SysUser) -> str:
    """
    为用户签发 JWT 登录令牌

    :param user: 登录成功的用户对象
    :return: 加密后的 Token 字符串
    """
    expire_seconds = current_app.config["JWT_EXPIRE_SECONDS"]
    payload = {
        "user_id": user.id,       # 用户ID
        "username": user.username,  # 用户名
        "role": user.role,        # 角色，便于快速判断权限
        "exp": datetime.utcnow() + timedelta(seconds=expire_seconds),  # 过期时间
        "iat": datetime.utcnow(),  # 签发时间
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def parse_token(token: str) -> dict:
    """
    解析 Token，取出载荷信息

    :param token: 前端传来的 Token 字符串
    :return: 载荷字典；解析失败返回 None
    """
    try:
        return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        # Token 已过期
        return None
    except jwt.InvalidTokenError:
        # Token 被篡改或格式错误
        return None


def get_current_user():
    """
    获取当前登录用户对象

    优先从 Flask 的上下文对象 g 中取（同一次请求内只查一次数据库），
    取不到时再根据 Token 查询数据库，并缓存到 g 中。

    :return: SysUser 对象；未登录返回 None
    """
    # 已经解析过，直接返回缓存结果
    if hasattr(g, "current_user"):
        return g.current_user

    g.current_user = None
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:].strip()
    payload = parse_token(token)
    if not payload:
        return None

    user = db.session.get(SysUser, payload.get("user_id"))
    if user and user.status == 1:
        g.current_user = user
    return g.current_user


def login_required(func):
    """
    登录校验装饰器

    用在需要登录才能访问的接口上，未登录或 Token 失效时返回 401。

    用法：
        @bp.route("/list")
        @login_required
        def list_data():
            ...
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return error("登录已过期，请重新登录", CODE_UNAUTHORIZED)
        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    """
    管理员权限装饰器

    在登录校验的基础上，额外要求当前用户角色为 admin，否则返回 403。
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return error("登录已过期，请重新登录", CODE_UNAUTHORIZED)
        if user.role != "admin":
            return error("无权限访问，该功能仅管理员可用", CODE_FORBIDDEN)
        return func(*args, **kwargs)

    return wrapper
