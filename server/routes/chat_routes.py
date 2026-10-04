# -*- coding: utf-8 -*-
"""
智能问答接口

包含两类功能：
  1. 会话管理：新建会话、会话列表、会话详情、重命名、删除
  2. 问答能力：普通问答接口 /ask 与流式问答接口 /stream（SSE，前端打字机效果）
"""
import json
from datetime import datetime

from flask import Blueprint, Response, request, stream_with_context

from models import ChatMessage, ChatSession, KnowledgeBase, SysUser, db
from rag.qa_chain import get_rag_service
from utils.auth import admin_required, get_current_user, login_required
from utils.response import error, page_result, success

chat_bp = Blueprint("chat", __name__)


# ===========================================================================
# 一、会话管理接口
# ===========================================================================

@chat_bp.route("/session/list", methods=["GET"])
@login_required
def session_list():
    """
    查询会话列表

    普通用户只能看到自己的会话；管理员可以通过 user_id 参数查看指定用户的会话。

    查询参数：
        page    页码
        size    每页条数
        keyword 标题关键字
        user_id 指定用户（仅管理员可用）
    """
    page = request.args.get("page", 1, type=int)
    size = request.args.get("size", 20, type=int)
    keyword = (request.args.get("keyword") or "").strip()
    user_id = request.args.get("user_id", type=int)

    current = get_current_user()
    query = ChatSession.query.filter(ChatSession.del_flag == 0)

    # 权限控制：普通用户只能查自己的
    if current.is_admin:
        if user_id:
            query = query.filter(ChatSession.user_id == user_id)
    else:
        query = query.filter(ChatSession.user_id == current.id)

    if keyword:
        query = query.filter(ChatSession.title.like(f"%{keyword}%"))

    pagination = db.paginate(
        query.order_by(ChatSession.update_time.desc()),
        page=page, per_page=size, error_out=False,
    )

    # 批量查询关联的知识库名称与用户名
    kb_ids = {s.kb_id for s in pagination.items if s.kb_id}
    user_ids = {s.user_id for s in pagination.items}
    kb_map = {kb.id: kb.name for kb in KnowledgeBase.query.filter(KnowledgeBase.id.in_(kb_ids)).all()} if kb_ids else {}
    user_map = {u.id: (u.nickname or u.username) for u in SysUser.query.filter(SysUser.id.in_(user_ids)).all()} if user_ids else {}

    items = [
        s.to_dict(kb_map.get(s.kb_id), user_map.get(s.user_id, "已删除用户"))
        for s in pagination.items
    ]
    return page_result(items, pagination.total, page, size)


@chat_bp.route("/session/create", methods=["POST"])
@login_required
def session_create():
    """
    新建会话

    请求体：{"kb_id": 1, "title": "新对话"}
    kb_id 可以不传或传 0，表示在全部知识库中检索。
    """
    data = request.get_json(silent=True) or {}
    kb_id = data.get("kb_id") or None
    if kb_id == 0:
        kb_id = None

    user = get_current_user()
    session = ChatSession(
        user_id=user.id,
        kb_id=kb_id,
        title=(data.get("title") or "新的对话").strip()[:200],
        message_count=0,
    )
    db.session.add(session)
    db.session.commit()
    return success(data=session.to_dict(), message="会话创建成功")


@chat_bp.route("/session/rename/<int:session_id>", methods=["PUT"])
@login_required
def session_rename(session_id: int):
    """
    重命名会话

    :param session_id: 会话ID
    """
    session = _get_own_session(session_id)
    if not session:
        return error("会话不存在")

    title = ((request.get_json(silent=True) or {}).get("title") or "").strip()
    if not title:
        return error("标题不能为空")

    session.title = title[:200]
    db.session.commit()
    return success(message="重命名成功")


@chat_bp.route("/session/delete/<int:session_id>", methods=["DELETE"])
@login_required
def session_delete(session_id: int):
    """
    删除会话（同时删除会话下的所有消息）

    :param session_id: 会话ID
    """
    session = _get_own_session(session_id)
    if not session:
        return error("会话不存在")

    ChatMessage.query.filter_by(session_id=session_id).delete()
    db.session.delete(session)
    db.session.commit()
    return success(message="会话已删除")


@chat_bp.route("/session/messages/<int:session_id>", methods=["GET"])
@login_required
def session_messages(session_id: int):
    """
    查询某个会话下的全部消息（按时间正序，用于前端还原聊天记录）

    :param session_id: 会话ID
    """
    session = _get_own_session(session_id)
    if not session:
        return error("会话不存在")

    messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.id.asc()).all()
    return success(data={
        "session": session.to_dict(),
        "messages": [msg.to_dict() for msg in messages],
    })


# ===========================================================================
# 二、问答接口
# ===========================================================================

@chat_bp.route("/ask", methods=["POST"])
@login_required
def ask():
    """
    普通问答接口（一次性返回完整答案）

    请求体：{"session_id": 1, "question": "年假有多少天？"}

    执行流程：
        保存提问 -> 检索知识库 -> 调用大模型 -> 保存回答 -> 返回结果
    """
    session, question, user_msg_id, err = _prepare_ask()
    if err:
        return err

    user = get_current_user()
    # 取出历史消息（用于多轮对话）。本轮提问此时已经入库，必须排除掉，
    # 否则它会同时出现在"历史对话"和"当前问题"里，被重复拼进提示词。
    history_records = (
        ChatMessage.query
        .filter(ChatMessage.session_id == session.id, ChatMessage.id != user_msg_id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    history = get_rag_service().build_history(history_records)

    # 调用 RAG 服务
    result = get_rag_service().ask(question, _resolve_kb_ids(session), history)
    # 补充引用来源所属的知识库名称，方便前端直接展示
    result["sources"] = _fill_kb_names(result["sources"])

    # 保存 AI 回答
    _save_answer(session, user.id, question, result["answer"], result["sources"], result["elapsed"])
    return success(data=result, message="回答完成")


@chat_bp.route("/stream", methods=["POST"])
@login_required
def stream():
    """
    流式问答接口（SSE，边生成边返回）

    请求体：{"session_id": 1, "question": "年假有多少天？"}

    返回格式为 text/event-stream，每条消息形如：
        data: {"type": "sources", "data": [...]}
        data: {"type": "message", "data": "答案片段"}
        data: {"type": "done", "data": {"elapsed": 3200}}

    前端使用 fetch + ReadableStream 读取，实现打字机效果。
    """
    session, question, user_msg_id, err = _prepare_ask()
    if err:
        return err

    user_id = get_current_user().id
    kb_ids = _resolve_kb_ids(session)

    # 先把历史消息查出来（生成器内部不能再查数据库，避免上下文丢失）。
    # 同样要排除本轮提问，避免问题被重复拼进提示词。
    history_records = (
        ChatMessage.query
        .filter(ChatMessage.session_id == session.id, ChatMessage.id != user_msg_id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    history = get_rag_service().build_history(history_records)
    session_id = session.id

    def generate():
        """SSE 事件生成器：把 RAG 服务产出的事件转换成 SSE 格式"""
        final_answer = ""
        sources = []
        elapsed = 0
        try:
            for event in get_rag_service().stream(question, kb_ids, history):
                if event["type"] == "sources":
                    # 补上知识库名称后再推送给前端
                    sources = _fill_kb_names(event["data"])
                    event["data"] = sources
                elif event["type"] == "done":
                    final_answer = event["data"].get("answer", "")
                    elapsed = event["data"].get("elapsed", 0)

                # SSE 要求每条消息以 "data: " 开头，以两个换行结尾
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # 流式输出结束后，把完整回答落库
            _save_answer_by_id(session_id, user_id, question, final_answer, sources, elapsed)
            yield "data: [DONE]\n\n"
        except Exception as exc:  # noqa: BLE001
            error_event = {"type": "error", "data": f"服务异常：{exc}"}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 关闭 Nginx 缓冲，保证实时输出
            "Connection": "keep-alive",
        },
    )


@chat_bp.route("/records", methods=["GET"])
@admin_required
def chat_records():
    """
    问答记录查询（管理员）：查看所有用户的提问与回答明细

    查询参数：
        page     页码
        size     每页条数
        keyword  问题内容关键字
        user_id  指定用户
        kb_id    指定知识库
    """
    page = request.args.get("page", 1, type=int)
    size = request.args.get("size", 10, type=int)
    keyword = (request.args.get("keyword") or "").strip()
    user_id = request.args.get("user_id", type=int)
    kb_id = request.args.get("kb_id", type=int)

    # 只查询用户提问的消息（每条提问对应其后的 AI 回答，这里以提问为维度展示）
    query = ChatMessage.query.filter(ChatMessage.role == ChatMessage.ROLE_USER)
    if keyword:
        query = query.filter(ChatMessage.content.like(f"%{keyword}%"))
    if user_id:
        query = query.filter(ChatMessage.user_id == user_id)
    if kb_id:
        query = query.filter(ChatMessage.kb_id == kb_id)

    pagination = db.paginate(
        query.order_by(ChatMessage.id.desc()),
        page=page, per_page=size, error_out=False,
    )

    # 批量取出对应的 AI 回答
    question_ids = [msg.id for msg in pagination.items]
    answer_map = {}
    if question_ids:
        answers = ChatMessage.query.filter(
            ChatMessage.role == ChatMessage.ROLE_ASSISTANT,
            ChatMessage.session_id.in_({msg.session_id for msg in pagination.items}),
        ).order_by(ChatMessage.id.asc()).all()
        # 同会话内，提问之后的第一条 AI 回答即为其答案
        for answer in answers:
            for question in pagination.items:
                if answer.session_id == question.session_id and answer.id > question.id:
                    answer_map.setdefault(question.id, answer)
                    break

    user_ids = {msg.user_id for msg in pagination.items}
    kb_ids = {msg.kb_id for msg in pagination.items if msg.kb_id}
    user_map = {u.id: (u.nickname or u.username) for u in SysUser.query.filter(SysUser.id.in_(user_ids)).all()} if user_ids else {}
    kb_map = {kb.id: kb.name for kb in KnowledgeBase.query.filter(KnowledgeBase.id.in_(kb_ids)).all()} if kb_ids else {}

    items = []
    for msg in pagination.items:
        answer = answer_map.get(msg.id)
        items.append({
            "id": msg.id,
            "user_id": msg.user_id,
            "username": user_map.get(msg.user_id, "已删除用户"),
            "kb_id": msg.kb_id,
            "kb_name": kb_map.get(msg.kb_id, "全部知识库"),
            "question": msg.content,
            "answer": answer.content if answer else "",
            "sources": answer.source_list() if answer else [],
            "response_time": answer.response_time if answer else 0,
            "create_time": msg.create_time.strftime("%Y-%m-%d %H:%M:%S") if msg.create_time else None,
        })
    return page_result(items, pagination.total, page, size)


# ===========================================================================
# 三、内部工具方法
# ===========================================================================

def _get_own_session(session_id: int):
    """
    获取会话对象，并校验当前用户是否有权访问

    管理员可以访问所有人的会话，普通用户只能访问自己的。

    :param session_id: 会话ID
    :return: ChatSession 对象；不存在或无权限时返回 None
    """
    session = ChatSession.query.filter_by(id=session_id, del_flag=0).first()
    if not session:
        return None

    current = get_current_user()
    if not current.is_admin and session.user_id != current.id:
        return None
    return session


def _prepare_ask():
    """
    问答接口的公共前置处理：参数校验 + 保存用户提问

    :return: (会话对象, 问题内容, 本轮提问消息ID, 错误响应)
             前三项有效时错误响应为 None；出错时前三项为 None。
             返回"本轮提问消息ID"是为了让调用方在查询历史消息时把它排除掉，
             否则当前问题会被重复拼进提示词。
    """
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    session_id = data.get("session_id")

    if not question:
        return None, None, None, error("请输入你的问题")
    if len(question) > 500:
        return None, None, None, error("问题太长了，请控制在 500 字以内")
    if not session_id:
        return None, None, None, error("缺少会话ID，请先创建会话")

    session = _get_own_session(int(session_id))
    if not session:
        return None, None, None, error("会话不存在")

    user = get_current_user()

    # 保存用户提问
    user_msg = ChatMessage(
        session_id=session.id,
        user_id=user.id,
        kb_id=session.kb_id,
        role=ChatMessage.ROLE_USER,
        content=question,
        response_time=0,
    )
    db.session.add(user_msg)

    # 首次提问时，用问题内容作为会话标题
    if session.message_count == 0 or not session.title or session.title == "新的对话":
        session.title = question[:30]

    session.message_count = (session.message_count or 0) + 1
    session.update_time = datetime.now()
    db.session.commit()

    return session, question, user_msg.id, None


def _fill_kb_names(sources: list) -> list:
    """
    为引用来源补充知识库名称

    RAG 模块（rag/vector_store.py）只返回 kb_id，这里统一查库补上 kb_name，
    这样前端展示引用来源时可以直接显示"来自哪个知识库"。

    :param sources: 引用来源列表，元素形如
                    {"file_name": "xx.pdf", "kb_id": 1, "score": 0.92, "content": "..."}
    :return: 补充了 kb_name 字段的来源列表（原地修改并返回）
    """
    if not sources:
        return sources

    kb_ids = {item.get("kb_id") for item in sources if item.get("kb_id")}
    if not kb_ids:
        return sources

    # 一次查出所有涉及的知识库名称，避免逐条查询
    kb_map = {
        kb.id: kb.name
        for kb in KnowledgeBase.query.filter(KnowledgeBase.id.in_(kb_ids)).all()
    }
    for item in sources:
        # 知识库被删除时兜底显示"未知知识库"
        item["kb_name"] = kb_map.get(item.get("kb_id"), "未知知识库")
    return sources


def _resolve_kb_ids(session) -> list:
    """
    确定本次问答要在哪些知识库中检索

    :param session: 会话对象
    :return: 知识库ID列表；会话未指定知识库时返回所有启用的知识库
    """
    if session.kb_id:
        return [session.kb_id]
    rows = KnowledgeBase.query.filter_by(del_flag=0, status=1).all()
    return [kb.id for kb in rows]


def _save_answer(session, user_id: int, question: str, answer: str,
                 sources: list, elapsed: int):
    """
    保存 AI 回答到数据库，并更新会话统计信息

    :param session: 会话对象
    :param user_id: 用户ID
    :param question: 用户问题（用于兜底生成标题）
    :param answer: AI 回答内容
    :param sources: 引用来源列表
    :param elapsed: 回答耗时（毫秒）
    """
    _save_answer_by_id(session.id, user_id, question, answer, sources, elapsed)


def _save_answer_by_id(session_id: int, user_id: int, question: str, answer: str,
                       sources: list, elapsed: int):
    """
    按会话ID保存 AI 回答（流式接口在生成器中使用，此时不能再依赖会话对象）

    :param session_id: 会话ID
    :param user_id: 用户ID
    :param question: 用户问题
    :param answer: AI 回答内容
    :param sources: 引用来源列表
    :param elapsed: 回答耗时（毫秒）
    """
    session = db.session.get(ChatSession, session_id)
    if not session:
        return

    ai_msg = ChatMessage(
        session_id=session_id,
        user_id=user_id,
        kb_id=session.kb_id,
        role=ChatMessage.ROLE_ASSISTANT,
        content=answer,
        # 来源列表以 JSON 字符串形式存储
        sources=json.dumps(sources, ensure_ascii=False) if sources else None,
        response_time=elapsed,
    )
    db.session.add(ai_msg)

    session.message_count = (session.message_count or 0) + 1
    session.update_time = datetime.now()
    if not session.title or session.title == "新的对话":
        session.title = question[:30]

    db.session.commit()
