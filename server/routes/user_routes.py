# -*- coding: utf-8 -*-
"""
用户管理接口（仅管理员可访问）

提供用户的增删改查、启用/禁用、重置密码等功能。
"""
from flask import Blueprint, request
from sqlalchemy import or_

from models import SysUser, db
from utils.auth import admin_required, get_current_user
from utils.password import md5_encrypt
from utils.response import error, page_result, success

user_bp = Blueprint("user", __name__)

# 新增用户时的默认密码
DEFAULT_PASSWORD = "123456"


@user_bp.route("/list", methods=["GET"])
@admin_required
def user_list():
    """
    分页查询用户列表

    查询参数：
        page    页码，默认 1
        size    每页条数，默认 10
        keyword 关键字，模糊匹配账号 / 昵称 / 手机号
        role    角色过滤：admin / user
        status  状态过滤：1 正常 / 0 禁用
    """
    page = request.args.get("page", 1, type=int)
    size = request.args.get("size", 10, type=int)
    keyword = (request.args.get("keyword") or "").strip()
    role = (request.args.get("role") or "").strip()
    status = request.args.get("status", type=int)

    # 组装查询条件
    query = SysUser.query
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(
            SysUser.username.like(like),
            SysUser.nickname.like(like),
            SysUser.phone.like(like),
        ))
    if role:
        query = query.filter(SysUser.role == role)
    if status is not None:
        query = query.filter(SysUser.status == status)

    # 按创建时间倒序分页
    pagination = db.paginate(
        query.order_by(SysUser.id.desc()),
        page=page, per_page=size, error_out=False,
    )
    items = [user.to_dict() for user in pagination.items]
    return page_result(items, pagination.total, page, size)


@user_bp.route("/create", methods=["POST"])
@admin_required
def create_user():
    """
    新增用户

    请求体：{"username": "xxx", "nickname": "昵称", "role": "user",
             "email": "xx@qq.com", "phone": "138...", "department": "研发中心"}
    新用户的初始密码统一为 123456（MD5 加密后存储）。
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    nickname = (data.get("nickname") or "").strip()

    if not username:
        return error("登录账号不能为空")
    if len(username) < 3:
        return error("登录账号长度不能少于 3 位")

    # 账号唯一性校验
    if SysUser.query.filter_by(username=username).first():
        return error("该登录账号已存在")

    role = data.get("role") or "user"
    if role not in ("admin", "user"):
        return error("角色只能是 admin 或 user")

    user = SysUser(
        username=username,
        # 密码统一使用 MD5 加密存储
        password=md5_encrypt(data.get("password") or DEFAULT_PASSWORD),
        nickname=nickname or username,
        email=(data.get("email") or "").strip(),
        phone=(data.get("phone") or "").strip(),
        department=(data.get("department") or "").strip(),
        role=role,
        status=1,
    )
    db.session.add(user)
    db.session.commit()
    return success(data=user.to_dict(), message=f"新增成功，初始密码为 {DEFAULT_PASSWORD}")


@user_bp.route("/update/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id: int):
    """
    修改用户信息（不含密码，密码请使用重置密码接口）

    :param user_id: 用户ID
    """
    user = db.session.get(SysUser, user_id)
    if not user:
        return error("用户不存在")

    data = request.get_json(silent=True) or {}

    # 账号允许修改，但要保证唯一
    new_username = (data.get("username") or "").strip()
    if new_username and new_username != user.username:
        if SysUser.query.filter_by(username=new_username).first():
            return error("该登录账号已存在")
        user.username = new_username

    role = data.get("role")
    if role:
        if role not in ("admin", "user"):
            return error("角色只能是 admin 或 user")
        # 防止把最后一个管理员降级为普通用户
        if user.role == "admin" and role == "user" and SysUser.query.filter_by(role="admin", status=1).count() <= 1:
            return error("系统至少需要保留一个管理员")
        user.role = role

    if "nickname" in data:
        user.nickname = (data.get("nickname") or "").strip() or user.nickname
    if "email" in data:
        user.email = (data.get("email") or "").strip()
    if "phone" in data:
        user.phone = (data.get("phone") or "").strip()
    if "department" in data:
        user.department = (data.get("department") or "").strip()

    db.session.commit()
    return success(data=user.to_dict(), message="修改成功")


@user_bp.route("/status/<int:user_id>", methods=["PUT"])
@admin_required
def change_status(user_id: int):
    """
    启用 / 禁用用户

    请求体：{"status": 1}  1=启用，0=禁用

    :param user_id: 用户ID
    """
    user = db.session.get(SysUser, user_id)
    if not user:
        return error("用户不存在")

    status = (request.get_json(silent=True) or {}).get("status")
    if status not in (0, 1):
        return error("状态值只能是 0 或 1")

    # 不允许禁用自己，也不允许禁用最后一个可用管理员
    current = get_current_user()
    if user.id == current.id:
        return error("不能修改自己的账号状态")
    if status == 0 and user.role == "admin" and SysUser.query.filter_by(role="admin", status=1).count() <= 1:
        return error("系统至少需要保留一个可用的管理员")

    user.status = status
    db.session.commit()
    return success(message="已启用该账号" if status == 1 else "已禁用该账号")


@user_bp.route("/reset-password/<int:user_id>", methods=["PUT"])
@admin_required
def reset_password(user_id: int):
    """
    重置用户密码为默认密码 123456

    :param user_id: 用户ID
    """
    user = db.session.get(SysUser, user_id)
    if not user:
        return error("用户不存在")

    user.password = md5_encrypt(DEFAULT_PASSWORD)
    db.session.commit()
    return success(message=f"密码已重置为 {DEFAULT_PASSWORD}")


@user_bp.route("/delete/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id: int):
    """
    删除用户

    说明：为了保留历史问答记录，这里采用物理删除用户记录、
    但问答记录不级联删除的策略，历史记录中的用户名会显示为"已删除用户"。

    :param user_id: 用户ID
    """
    user = db.session.get(SysUser, user_id)
    if not user:
        return error("用户不存在")

    current = get_current_user()
    if user.id == current.id:
        return error("不能删除自己的账号")
    if user.role == "admin" and SysUser.query.filter_by(role="admin").count() <= 1:
        return error("系统至少需要保留一个管理员")

    db.session.delete(user)
    db.session.commit()
    return success(message="删除成功")


@user_bp.route("/options", methods=["GET"])
@admin_required
def user_options():
    """
    获取用户下拉选项列表（供问答记录页面的筛选框使用）

    :return: [{"id": 1, "username": "admin", "nickname": "超级管理员"}, ...]
    """
    users = SysUser.query.order_by(SysUser.id.asc()).all()
    options = [
        {"id": u.id, "username": u.username, "nickname": u.nickname or u.username, "role": u.role}
        for u in users
    ]
    return success(data=options)
