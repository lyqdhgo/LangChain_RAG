# -*- coding: utf-8 -*-
"""
数据统计接口（管理员首页使用）

为首页的统计卡片与图表提供数据，包含：
    /overview          顶部统计卡片（用户数、知识库数、文档数、问答数等）
    /trend             最近 N 天的问答量趋势（折线图）
    /kb-rank           各知识库文档数量排行（柱状图）
    /user-rank         提问最多的用户排行（横向柱状图）
    /category          知识库分类占比（饼图）
    /doc-status        文档处理状态分布（环形图）
    /recent-questions  最新提问列表（表格）
"""
from datetime import date, datetime, timedelta

from flask import Blueprint, request
from sqlalchemy import func

from models import ChatMessage, ChatSession, KbDocument, KnowledgeBase, SysUser, db
from utils.auth import admin_required
from utils.response import success

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/overview", methods=["GET"])
@admin_required
def overview():
    """
    顶部统计卡片数据

    :return: {
        "user_count": 用户总数,
        "kb_count": 知识库总数,
        "doc_count": 文档总数,
        "chunk_count": 向量片段总数,
        "question_count": 累计提问数,
        "today_question_count": 今日提问数,
        "session_count": 会话总数,
        "active_user_count": 近 7 天有提问的用户数
    }
    """
    today_start = datetime.combine(date.today(), datetime.min.time())
    week_start = datetime.now() - timedelta(days=7)

    # 累计提问数（只统计 role=user 的消息）
    question_count = ChatMessage.query.filter_by(role=ChatMessage.ROLE_USER).count()
    today_question_count = ChatMessage.query.filter(
        ChatMessage.role == ChatMessage.ROLE_USER,
        ChatMessage.create_time >= today_start,
    ).count()

    # 向量片段总数 = 所有文档的 chunk_count 之和
    chunk_total = db.session.query(func.coalesce(func.sum(KbDocument.chunk_count), 0)).filter(
        KbDocument.del_flag == 0
    ).scalar() or 0

    active_user_count = db.session.query(
        func.count(func.distinct(ChatMessage.user_id))
    ).filter(
        ChatMessage.role == ChatMessage.ROLE_USER,
        ChatMessage.create_time >= week_start,
    ).scalar() or 0

    return success(data={
        "user_count": SysUser.query.count(),
        "kb_count": KnowledgeBase.query.filter_by(del_flag=0).count(),
        "doc_count": KbDocument.query.filter_by(del_flag=0).count(),
        "chunk_count": int(chunk_total),
        "question_count": question_count,
        "today_question_count": today_question_count,
        "session_count": ChatSession.query.filter_by(del_flag=0).count(),
        "active_user_count": int(active_user_count),
    })


@stats_bp.route("/trend", methods=["GET"])
@admin_required
def trend():
    """
    最近 N 天的问答量趋势（折线图）

    查询参数：days 统计天数，默认 7，可选 7 / 15 / 30

    :return: {"dates": ["09-28", ...], "questions": [3, 5, ...], "sessions": [2, 4, ...]}
    """
    days = request.args.get("days", 7, type=int)
    if days not in (7, 15, 30):
        days = 7

    start_day = date.today() - timedelta(days=days - 1)

    # 按日期分组统计提问量
    question_rows = db.session.query(
        func.date(ChatMessage.create_time).label("day"),
        func.count(ChatMessage.id),
    ).filter(
        ChatMessage.role == ChatMessage.ROLE_USER,
        ChatMessage.create_time >= datetime.combine(start_day, datetime.min.time()),
    ).group_by("day").all()
    question_map = {str(day): count for day, count in question_rows}

    # 按日期分组统计会话数
    session_rows = db.session.query(
        func.date(ChatSession.create_time).label("day"),
        func.count(ChatSession.id),
    ).filter(
        ChatSession.create_time >= datetime.combine(start_day, datetime.min.time()),
        ChatSession.del_flag == 0,
    ).group_by("day").all()
    session_map = {str(day): count for day, count in session_rows}

    # 补齐没有数据的日期，避免折线图出现断点
    dates, questions, sessions = [], [], []
    for offset in range(days):
        current = start_day + timedelta(days=offset)
        key = current.strftime("%Y-%m-%d")
        dates.append(current.strftime("%m-%d"))
        questions.append(question_map.get(key, 0))
        sessions.append(session_map.get(key, 0))

    return success(data={"dates": dates, "questions": questions, "sessions": sessions})


@stats_bp.route("/kb-rank", methods=["GET"])
@admin_required
def kb_rank():
    """
    各知识库的文档数量与向量片段数量（柱状图）

    :return: {"names": [...], "doc_counts": [...], "chunk_counts": [...]}
    """
    rows = db.session.query(
        KnowledgeBase.name,
        func.count(KbDocument.id).label("doc_count"),
        func.coalesce(func.sum(KbDocument.chunk_count), 0).label("chunk_count"),
    ).outerjoin(
        KbDocument, (KbDocument.kb_id == KnowledgeBase.id) & (KbDocument.del_flag == 0)
    ).filter(
        KnowledgeBase.del_flag == 0
    ).group_by(KnowledgeBase.id).order_by(func.count(KbDocument.id).desc()).all()

    return success(data={
        "names": [row[0] for row in rows],
        "doc_counts": [int(row[1]) for row in rows],
        "chunk_counts": [int(row[2]) for row in rows],
    })


@stats_bp.route("/user-rank", methods=["GET"])
@admin_required
def user_rank():
    """
    提问最多的用户排行（横向柱状图），取前 6 名

    :return: {"names": [...], "counts": [...]}
    """
    rows = db.session.query(
        SysUser.nickname, SysUser.username, func.count(ChatMessage.id).label("cnt"),
    ).join(
        ChatMessage, ChatMessage.user_id == SysUser.id
    ).filter(
        ChatMessage.role == ChatMessage.ROLE_USER
    ).group_by(SysUser.id).order_by(func.count(ChatMessage.id).desc()).limit(6).all()

    return success(data={
        "names": [(row[0] or row[1]) for row in rows],
        "counts": [int(row[2]) for row in rows],
    })


@stats_bp.route("/category", methods=["GET"])
@admin_required
def category():
    """
    知识库分类占比（饼图）

    :return: [{"name": "技术文档", "value": 2}, ...]
    """
    rows = db.session.query(
        KnowledgeBase.category, func.count(KnowledgeBase.id),
    ).filter(
        KnowledgeBase.del_flag == 0
    ).group_by(KnowledgeBase.category).all()

    return success(data=[{"name": row[0] or "未分类", "value": int(row[1])} for row in rows])


@stats_bp.route("/doc-status", methods=["GET"])
@admin_required
def doc_status():
    """
    文档处理状态分布（环形图）

    :return: [{"name": "已完成", "value": 12}, ...]
    """
    rows = db.session.query(
        KbDocument.status, func.count(KbDocument.id),
    ).filter(
        KbDocument.del_flag == 0
    ).group_by(KbDocument.status).all()

    # 状态码转成中文名称
    status_names = {0: "待处理", 1: "向量化中", 2: "已完成", 3: "失败"}
    data = [{"name": status_names.get(status, "未知"), "value": int(count)} for status, count in rows]

    # 保证四个状态都有值，图表图例才完整
    exists = {item["name"] for item in data}
    for code, name in status_names.items():
        if name not in exists:
            data.append({"name": name, "value": 0})
    return success(data=data)


@stats_bp.route("/recent-questions", methods=["GET"])
@admin_required
def recent_questions():
    """
    最新提问列表（首页表格），默认取最近 8 条

    :return: [{"username": "张三", "question": "...", "create_time": "..."}]
    """
    limit = request.args.get("limit", 8, type=int)
    rows = db.session.query(ChatMessage, SysUser).outerjoin(
        SysUser, SysUser.id == ChatMessage.user_id
    ).filter(
        ChatMessage.role == ChatMessage.ROLE_USER
    ).order_by(ChatMessage.id.desc()).limit(limit).all()

    items = []
    for msg, user in rows:
        items.append({
            "id": msg.id,
            "username": (user.nickname or user.username) if user else "已删除用户",
            "question": msg.content,
            "create_time": msg.create_time.strftime("%Y-%m-%d %H:%M:%S") if msg.create_time else None,
        })
    return success(data=items)
