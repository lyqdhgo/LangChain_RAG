# -*- coding: utf-8 -*-
"""
项目配置文件

集中管理数据库、JWT、文件上传、Ollama 大模型、Chroma 向量库等所有配置项。
支持通过 .env 文件或系统环境变量覆盖默认值，方便在不同环境部署。
"""
import os

from dotenv import load_dotenv

# 读取项目根目录下的 .env 文件（如果存在）
load_dotenv()

# 项目根路径（server 目录的绝对路径）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """
    全局配置类

    所有配置项均以类属性的形式提供，Flask 通过 app.config.from_object(Config) 加载。
    取值优先级：环境变量 > .env 文件 > 代码中的默认值。
    """

    # ------------------------------------------------------------------
    # 一、Flask 基础配置
    # ------------------------------------------------------------------
    # 密钥，用于 JWT 签名，生产环境请务必修改
    SECRET_KEY = os.getenv("SECRET_KEY", "enterprise-qa-secret-key-2024")
    # 开启调试模式，代码修改后会自动重启
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    # 允许返回中文，不做 ASCII 转义
    JSON_AS_ASCII = False
    # 单次请求体最大 50MB（用于上传文档）
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024

    # ------------------------------------------------------------------
    # 二、MySQL 数据库配置（端口 3308）
    # ------------------------------------------------------------------
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3308))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "db_enterprise_qa")

    # SQLAlchemy 连接串，charset 必须指定为 utf8mb4 才能存储中文与 emoji
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    )
    # 关闭对象修改追踪，可以节省内存
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 连接池配置：超时自动回收，避免 MySQL 主动断开导致的 "Lost connection"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # 取出连接前先 ping 一下，断开的连接自动重建
        "pool_recycle": 3600,    # 1 小时回收一次连接
        "pool_size": 10,
        "max_overflow": 20,
    }

    # ------------------------------------------------------------------
    # 三、JWT 登录令牌配置
    # ------------------------------------------------------------------
    # 令牌有效期（秒），默认 7 天
    JWT_EXPIRE_SECONDS = int(os.getenv("JWT_EXPIRE_SECONDS", 7 * 24 * 3600))

    # ------------------------------------------------------------------
    # 四、文件上传配置
    # ------------------------------------------------------------------
    # 上传文件保存目录
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    # 允许上传的文件后缀
    ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt", "md", "csv"}

    # ------------------------------------------------------------------
    # 五、Ollama 大模型配置
    # ------------------------------------------------------------------
    # Ollama 服务地址
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    # 对话大模型
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:8b")
    # 嵌入（向量化）模型
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "qwen3-embedding:4b")
    # 模型温度，越低回答越稳定，知识库问答建议 0~0.3
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.1))

    # ------------------------------------------------------------------
    # 六、Chroma 向量数据库配置
    # ------------------------------------------------------------------
    # 向量数据持久化目录
    CHROMA_DIR = os.getenv("CHROMA_DIR", os.path.join(BASE_DIR, "chroma_db"))
    # 检索时返回的相似文本块数量
    RETRIEVE_TOP_K = int(os.getenv("RETRIEVE_TOP_K", 4))
    # 相似度过滤阈值：项目使用余弦距离（distance = 1 - 余弦相似度），值越小越相似，
    # 距离大于该阈值的片段会被丢弃。取值范围 0~2：
    #   调小（如 0.6）→ 只保留高度相关的片段，回答更严谨但可能漏召回
    #   调大（如 1.2）→ 召回更多片段，但可能引入无关内容
    RETRIEVE_SCORE_THRESHOLD = float(os.getenv("RETRIEVE_SCORE_THRESHOLD", 1.0))

    # ------------------------------------------------------------------
    # 七、文本切分配置
    # ------------------------------------------------------------------
    # 每个文本块的最大字符数
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))
    # 相邻文本块的重叠字符数，用于保持语义连贯
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 80))
