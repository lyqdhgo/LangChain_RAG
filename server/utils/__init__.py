# -*- coding: utf-8 -*-
"""
工具包

包含统一响应封装、密码加密、登录鉴权等通用能力。
"""
from utils.response import success, error, page_result
from utils.password import md5_encrypt, verify_password
from utils.auth import login_required, admin_required, get_current_user

__all__ = [
    "success",
    "error",
    "page_result",
    "md5_encrypt",
    "verify_password",
    "login_required",
    "admin_required",
    "get_current_user",
]
