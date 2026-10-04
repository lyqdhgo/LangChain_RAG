# -*- coding: utf-8 -*-
"""
数据模型包

统一在此处创建 SQLAlchemy 实例并导出所有 ORM 模型，
其他模块只需要 `from models import db, SysUser` 即可使用。
"""
from flask_sqlalchemy import SQLAlchemy

# 全局唯一的数据库操作对象，在 app.py 中通过 db.init_app(app) 完成绑定
db = SQLAlchemy()

# 导入各业务模型（必须在 db 创建之后导入，否则会循环依赖）
from models.user import SysUser                      # noqa: E402
from models.knowledge import KnowledgeBase, KbDocument  # noqa: E402
from models.chat import ChatSession, ChatMessage     # noqa: E402

__all__ = [
    "db",
    "SysUser",
    "KnowledgeBase",
    "KbDocument",
    "ChatSession",
    "ChatMessage",
]
