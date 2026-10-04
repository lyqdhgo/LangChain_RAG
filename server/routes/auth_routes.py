# -*- coding: utf-8 -*-
"""
认证相关接口

提供登录、获取当前用户信息、修改密码、修改个人资料等功能。
"""
from datetime import datetime

from flask import Blueprint, current_app, request

from models import SysUser, db
from rag.embeddings import check_ollama_status
from utils.auth import admin_required, create_token, get_current_user, login_required
from utils.password import md5_encrypt, verify_password
from utils.response import error, success

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    用户登录接口

    请求体：{"username": "admin", "password": "123456"}
    返回：{"token": "xxx", "user": {...}}

    校验逻辑：密码使用 MD5 加密后与数据库中的密文比对。
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return error("账号和密码不能为空")

    # 根据账号查询用户
    user = SysUser.query.filter_by(username=username).first()
    if not user:
        return error("账号或密码错误")

    # 校验密码（数据库中存的是 MD5 密文）
    if not verify_password(password, user.password):
        return error("账号或密码错误")

    # 校验账号状态
    if user.status != 1:
        return error("账号已被禁用，请联系管理员")

    # 更新最近登录时间
    user.last_login_time = datetime.now()
    db.session.commit()

    token = create_token(user)
    return success(
        data={"token": token, "user": user.to_dict()},
        message="登录成功",
    )


@auth_bp.route("/info", methods=["GET"])
@login_required
def get_info():
    """
    获取当前登录用户的信息

    前端刷新页面后调用该接口恢复登录状态。
    """
    user = get_current_user()
    return success(data=user.to_dict())


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """
    退出登录

    JWT 是无状态令牌，服务端不保存会话，因此这里只做形式上的响应，
    真正的登出由前端删除本地保存的 Token 完成。
    """
    return success(message="退出成功")


@auth_bp.route("/password", methods=["PUT"])
@login_required
def update_password():
    """
    修改当前用户的登录密码

    请求体：{"old_password": "123456", "new_password": "654321"}
    """
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""

    if not old_password or not new_password:
        return error("原密码和新密码都不能为空")
    if len(new_password) < 6:
        return error("新密码长度不能少于 6 位")
    if not verify_password(old_password, user.password):
        return error("原密码不正确")
    if old_password == new_password:
        return error("新密码不能与原密码相同")

    # 新密码同样使用 MD5 加密后保存
    user.password = md5_encrypt(new_password)
    db.session.commit()
    return success(message="密码修改成功，请重新登录")


@auth_bp.route("/profile", methods=["PUT"])
@login_required
def update_profile():
    """
    修改当前用户的个人资料（昵称、邮箱、手机号）

    请求体：{"nickname": "张三", "email": "xx@qq.com", "phone": "13800000000"}
    """
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    if "nickname" in data:
        user.nickname = (data.get("nickname") or "").strip() or user.nickname
    if "email" in data:
        user.email = (data.get("email") or "").strip()
    if "phone" in data:
        user.phone = (data.get("phone") or "").strip()

    db.session.commit()
    return success(data=user.to_dict(), message="资料修改成功")


@auth_bp.route("/system/status", methods=["GET"])
def system_status():
    """
    获取系统运行状态（供登录页 / 个人中心展示）

    注意：本接口刻意不加 @login_required。
    因为登录页需要在用户登录之前就展示"AI 模型是否就绪"，加了登录校验会导致
    登录页永远拿不到数据（401）。返回内容仅包含模型名称与在线状态这类
    低敏感信息，与公开的 /api/health 一致。

    返回内容：Ollama 服务是否在线、所需模型是否已下载、当前使用的模型名称。
    """
    status = check_ollama_status()
    return success(data={
        "ollama_online": status["online"],
        "ollama_models": status["models"],
        "missing_models": status["missing"],
        "llm_model": current_app.config["LLM_MODEL"],
        "embedding_model": current_app.config["EMBEDDING_MODEL"],
    })
