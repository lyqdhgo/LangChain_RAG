# -*- coding: utf-8 -*-
"""
知识库相关模型

包含两张表：
  - kb_knowledge_base：知识库（一个知识库对应 Chroma 中的一个 collection）
  - kb_document      ：知识库中的文档（一个文档会被切分成多个文本块存入向量库）
"""
from datetime import datetime

from models import db


class KnowledgeBase(db.Model):
    """
    知识库模型

    每个知识库在 Chroma 向量数据库中对应一个独立的 collection，
    命名规则为 `kb_{id}`，这样可以做到不同知识库之间的数据隔离。
    """

    __tablename__ = "kb_knowledge_base"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    name = db.Column(db.String(100), nullable=False, comment="知识库名称")
    description = db.Column(db.String(500), comment="知识库描述")
    category = db.Column(db.String(50), default="通用", comment="知识库分类")
    cover_color = db.Column(db.String(20), default="#409EFF", comment="前端卡片主题色")
    creator_id = db.Column(db.BigInteger, nullable=False, comment="创建人ID")
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment="状态：1=启用 0=停用")
    del_flag = db.Column(db.SmallInteger, nullable=False, default=0, comment="删除标记：0=正常 1=已删除")
    create_time = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def to_dict(self, doc_count: int = None) -> dict:
        """
        将知识库对象转换为字典

        :param doc_count: 该知识库下的文档数量，由调用方统计后传入（避免 N+1 查询）
        :return: 字典形式的知识库信息
        """
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "cover_color": self.cover_color,
            "creator_id": self.creator_id,
            "status": self.status,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S") if self.create_time else None,
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S") if self.update_time else None,
        }
        if doc_count is not None:
            data["doc_count"] = doc_count
        return data

    def __repr__(self) -> str:
        """调试时打印对象信息"""
        return f"<KnowledgeBase {self.id} {self.name}>"


class KbDocument(db.Model):
    """
    知识库文档模型

    status 字段说明（前端会按照该字段显示不同颜色的标签）：
      0 = 待处理   1 = 向量化中   2 = 已完成   3 = 失败
    """

    __tablename__ = "kb_document"

    # 文档处理状态常量，避免代码中出现魔法数字
    STATUS_PENDING = 0      # 待处理
    STATUS_PROCESSING = 1   # 向量化中
    STATUS_SUCCESS = 2      # 已完成
    STATUS_FAILED = 3       # 失败

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    kb_id = db.Column(db.BigInteger, nullable=False, comment="所属知识库ID")
    file_name = db.Column(db.String(255), nullable=False, comment="原始文件名")
    file_path = db.Column(db.String(500), comment="服务器本地存储路径")
    file_type = db.Column(db.String(20), comment="文件类型")
    file_size = db.Column(db.BigInteger, default=0, comment="文件大小（字节）")
    chunk_count = db.Column(db.Integer, default=0, comment="切分后的文本块数量")
    char_count = db.Column(db.Integer, default=0, comment="文档总字符数")
    status = db.Column(db.SmallInteger, nullable=False, default=0, comment="处理状态")
    error_msg = db.Column(db.String(500), comment="失败原因")
    uploader_id = db.Column(db.BigInteger, nullable=False, comment="上传人ID")
    del_flag = db.Column(db.SmallInteger, nullable=False, default=0, comment="删除标记")
    create_time = db.Column(db.DateTime, default=datetime.now, comment="上传时间")
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def to_dict(self, kb_name: str = None, uploader_name: str = None) -> dict:
        """
        将文档对象转换为字典

        :param kb_name: 所属知识库名称（列表展示时使用）
        :param uploader_name: 上传人昵称（列表展示时使用）
        :return: 字典形式的文档信息
        """
        size = self.file_size or 0
        data = {
            "id": self.id,
            "kb_id": self.kb_id,
            "kb_name": kb_name,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": size,
            # 友好显示的文件大小，如 512.0 KB
            "file_size_text": self._format_size(size),
            "chunk_count": self.chunk_count or 0,
            "char_count": self.char_count or 0,
            "status": self.status,
            "error_msg": self.error_msg,
            "uploader_id": self.uploader_id,
            "uploader_name": uploader_name,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S") if self.create_time else None,
        }
        return data

    @staticmethod
    def _format_size(size: int) -> str:
        """
        将字节数格式化为易读的字符串

        :param size: 文件字节数
        :return: 例如 "1.25 MB"
        """
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / 1024 / 1024:.2f} MB"

    def __repr__(self) -> str:
        """调试时打印对象信息"""
        return f"<KbDocument {self.id} {self.file_name} status={self.status}>"
