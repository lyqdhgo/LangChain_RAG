# -*- coding: utf-8 -*-
"""
问答相关模型

包含两张表：
  - chat_session：一次连续的对话（会话）
  - chat_message：会话中的每一条消息（用户提问 / AI 回答）
"""
import json
from datetime import datetime

from models import db


class ChatSession(db.Model):
    """
    问答会话模型

    用户每开启一轮新的问答就会创建一个会话，会话标题默认取第一个问题的前 30 个字符。
    """

    __tablename__ = "chat_session"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    user_id = db.Column(db.BigInteger, nullable=False, comment="所属用户ID")
    kb_id = db.Column(db.BigInteger, comment="关联知识库ID，为空表示全部知识库")
    title = db.Column(db.String(200), default="新的对话", comment="会话标题")
    message_count = db.Column(db.Integer, nullable=False, default=0, comment="会话消息条数")
    del_flag = db.Column(db.SmallInteger, nullable=False, default=0, comment="删除标记")
    create_time = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="最后活跃时间")

    def to_dict(self, kb_name: str = None, username: str = None) -> dict:
        """
        将会话对象转换为字典

        :param kb_name: 关联知识库名称
        :param username: 会话所属用户名（管理端问答记录页面使用）
        :return: 字典形式的会话信息
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": username,
            "kb_id": self.kb_id,
            "kb_name": kb_name,
            "title": self.title,
            "message_count": self.message_count,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S") if self.create_time else None,
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S") if self.update_time else None,
        }

    def __repr__(self) -> str:
        """调试时打印对象信息"""
        return f"<ChatSession {self.id} user={self.user_id} title={self.title}>"


class ChatMessage(db.Model):
    """
    问答消息模型

    role 字段：
      - user      ：用户提问
      - assistant ：AI 回答
    sources 字段存储引用来源的 JSON 字符串，形如：
      [{"file_name": "xx.pdf", "kb_name": "技术文档", "score": 0.92}]
    """

    __tablename__ = "chat_message"

    ROLE_USER = "user"            # 用户提问
    ROLE_ASSISTANT = "assistant"  # AI 回答

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    session_id = db.Column(db.BigInteger, nullable=False, comment="所属会话ID")
    user_id = db.Column(db.BigInteger, nullable=False, comment="提问用户ID")
    kb_id = db.Column(db.BigInteger, comment="命中的知识库ID")
    role = db.Column(db.String(20), nullable=False, comment="消息角色：user/assistant")
    content = db.Column(db.Text, comment="消息内容")
    sources = db.Column(db.Text, comment="引用来源（JSON 字符串）")
    response_time = db.Column(db.Integer, default=0, comment="AI 回答耗时（毫秒）")
    create_time = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    def source_list(self) -> list:
        """
        将 sources 字段的 JSON 字符串解析成列表

        :return: 来源列表，解析失败时返回空列表
        """
        if not self.sources:
            return []
        try:
            return json.loads(self.sources)
        except (ValueError, TypeError):
            return []

    def to_dict(self) -> dict:
        """
        将消息对象转换为字典

        :return: 字典形式的消息信息
        """
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "kb_id": self.kb_id,
            "role": self.role,
            "content": self.content,
            "sources": self.source_list(),
            "response_time": self.response_time,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S") if self.create_time else None,
        }

    def __repr__(self) -> str:
        """调试时打印对象信息"""
        return f"<ChatMessage {self.id} {self.role} session={self.session_id}>"
