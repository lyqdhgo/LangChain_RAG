# -*- coding: utf-8 -*-
"""
企业知识库问答系统 - Flask 后端启动入口

启动方式：
    python app.py
默认监听：http://127.0.0.1:5000

启动前请确认：
    1. MySQL8 已启动，且 3308 端口已执行过 sql/db_enterprise_qa.sql 脚本
    2. Ollama 已启动，且已下载 qwen3:8b 与 qwen3-embedding:4b 两个模型
"""
import logging
import os
import sys

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

# 把当前目录加入模块搜索路径，保证在任意目录下都能用 python app.py 启动
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config          # noqa: E402
from models import db              # noqa: E402
from routes import register_blueprints  # noqa: E402


def create_app() -> Flask:
    """
    应用工厂：创建并配置 Flask 应用

    :return: 配置完成的 Flask 应用实例
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # 让返回的 JSON 支持中文（不转义成 \\uXXXX）
    app.json.ensure_ascii = False

    # 配置日志格式，方便在控制台观察执行过程
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 允许跨域，前端开发服务器（默认 5173 端口）需要访问后端接口
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # 初始化数据库
    db.init_app(app)

    # 创建必需的工作目录
    _init_directories(app)

    # 注册所有接口蓝图
    register_blueprints(app)

    # 注册全局异常处理与健康检查
    _register_error_handler(app)
    _register_health_check(app)

    return app


def _init_directories(app: Flask):
    """
    创建运行所需的工作目录（上传目录、向量库目录）

    :param app: Flask 应用实例
    """
    for key in ("UPLOAD_FOLDER", "CHROMA_DIR"):
        path = app.config[key]
        os.makedirs(path, exist_ok=True)


def _register_error_handler(app: Flask):
    """
    注册全局异常处理器

    保证任何未捕获的异常都返回统一格式的 JSON，而不是 HTML 错误页，
    这样前端拦截器才能正确处理。

    :param app: Flask 应用实例
    """

    @app.errorhandler(Exception)
    def handle_exception(exc):
        """统一异常处理：把异常转换成 {code, message, data} 结构"""
        # 回滚数据库会话，避免脏数据影响后续请求
        db.session.rollback()

        # HTTP 异常（如 404、405）保留原始状态码
        if isinstance(exc, HTTPException):
            app.logger.warning("HTTP 异常：%s %s", exc.code, exc.description)
            return jsonify({"code": exc.code, "message": exc.description, "data": None}), 200

        # 其他异常打印完整堆栈，便于排查
        app.logger.exception("服务器内部错误")
        return jsonify({"code": 500, "message": f"服务器内部错误：{exc}", "data": None}), 200


def _register_health_check(app: Flask):
    """
    注册健康检查接口

    :param app: Flask 应用实例
    """

    @app.route("/api/health", methods=["GET"])
    def health():
        """健康检查：返回服务与数据库连接状态"""
        from rag.embeddings import check_ollama_status
        from sqlalchemy import text

        result = {"server": "ok", "mysql": "unknown", "ollama": "unknown"}
        try:
            db.session.execute(text("SELECT 1"))
            result["mysql"] = "ok"
        except Exception as exc:  # noqa: BLE001
            result["mysql"] = f"error: {exc}"

        status = check_ollama_status()
        result["ollama"] = "ok" if status["online"] else "offline"
        result["ollama_missing_models"] = status["missing"]

        return jsonify({"code": 200, "message": "服务运行中", "data": result})


# 创建应用实例（供 flask run 与 python app.py 两种方式共用）
app = create_app()


if __name__ == "__main__":
    print("=" * 66)
    print("  企业知识库问答系统（LangChain + RAG）后端服务")
    print(f"  服务地址：http://127.0.0.1:5000")
    print(f"  健康检查：http://127.0.0.1:5000/api/health")
    print(f"  对话模型：{app.config['LLM_MODEL']}")
    print(f"  嵌入模型：{app.config['EMBEDDING_MODEL']}")
    print("=" * 66)
    app.run(host="0.0.0.0", port=5000, debug=app.config["DEBUG"], threaded=True)
