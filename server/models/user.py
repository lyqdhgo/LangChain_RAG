# -*- coding: utf-8 -*-
"""
用户模型

对应数据表：sys_user
"""
from datetime import datetime

from models import db


class SysUser(db.Model):
    """
    系统用户表模型

    系统分为两种角色：
      - admin：管理员，可以管理知识库、文档、用户，并查看统计首页
      - user ：普通用户，只能与知识库进行问答、查看自己的历史会话
    """

    __tablename__ = "sys_user"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    username = db.Column(db.String(50), nullable=False, unique=True, comment="登录账号")
    password = db.Column(db.String(64), nullable=False, comment="MD5 加密后的密码")
    nickname = db.Column(db.String(50), comment="用户昵称")
    email = db.Column(db.String(100), comment="邮箱")
    phone = db.Column(db.String(20), comment="手机号")
    avatar = db.Column(db.String(255), comment="头像地址")
    role = db.Column(db.String(20), nullable=False, default="user", comment="角色：admin/user")
    department = db.Column(db.String(50), comment="所属部门")
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment="状态：1=正常 0=禁用")
    last_login_time = db.Column(db.DateTime, comment="最近登录时间")
    create_time = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def to_dict(self, with_password: bool = False) -> dict:
        """
        将模型对象转换为字典，用于返回给前端

        :param with_password: 是否包含密码字段，默认 False（安全考虑不返回密码）
        :return: 字典形式的用户信息
        """
        data = {
            "id": self.id,
            "username": self.username,
            "nickname": self.nickname,
            "email": self.email,
            "phone": self.phone,
            "avatar": self.avatar,
            "role": self.role,
            "department": self.department,
            "status": self.status,
            "last_login_time": self.last_login_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_login_time else None,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S") if self.create_time else None,
        }
        if with_password:
            data["password"] = self.password
        return data

    @property
    def is_admin(self) -> bool:
        """判断当前用户是否为管理员"""
        return self.role == "admin"

    def __repr__(self) -> str:
        """调试时打印对象信息"""
        return f"<SysUser {self.id} {self.username} {self.role}>"
