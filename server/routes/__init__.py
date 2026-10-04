# -*- coding: utf-8 -*-
"""
路由包

统一注册所有接口蓝图，所有接口统一以 /api 作为前缀。
接口分类：
    /api/auth   —— 登录、登出、个人信息
    /api/user   —— 用户管理（管理员）
    /api/kb     —— 知识库与文档管理
    /api/chat   —— 智能问答与会话记录
    /api/stats  —— 首页统计数据
"""


def register_blueprints(app):
    """
    把所有蓝图注册到 Flask 应用上

    :param app: Flask 应用实例
    """
    # 在函数内部导入，避免循环引用
    from routes.auth_routes import auth_bp
    from routes.user_routes import user_bp
    from routes.kb_routes import kb_bp
    from routes.chat_routes import chat_bp
    from routes.stats_routes import stats_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(kb_bp, url_prefix="/api/kb")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(stats_bp, url_prefix="/api/stats")
    app.logger.info("所有接口蓝图注册完成")
