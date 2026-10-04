# -*- coding: utf-8 -*-
"""
知识库与文档管理接口

知识库相关接口仅管理员可以增删改，普通用户可以查看列表（用于问答时选择范围）。
文档上传后会自动进行"解析 -> 切分 -> 向量化"，处理过程放在后台线程中执行，
接口会立即返回，前端通过文档状态字段轮询处理进度。
"""
import os
import re
import threading
import uuid

from flask import Blueprint, current_app, request
from sqlalchemy import func

from models import KbDocument, KnowledgeBase, SysUser, db
from rag.document_loader import count_chars, load_and_split
from rag.vector_store import add_documents, delete_by_doc_id, delete_collection
from utils.auth import admin_required, get_current_user, login_required
from utils.response import error, page_result, success

kb_bp = Blueprint("kb", __name__)

# 知识库封面可选主题色（前端新建知识库时展示）
COVER_COLORS = ["#409EFF", "#67C23A", "#E6A23C", "#F56C6C", "#909399", "#9254DE", "#13C2C2"]


# ===========================================================================
# 一、知识库相关接口
# ===========================================================================

@kb_bp.route("/list", methods=["GET"])
@login_required
def kb_list():
    """
    分页查询知识库列表

    查询参数：
        page     页码，默认 1
        size     每页条数，默认 8
        keyword  名称关键字
        category 分类过滤
        all      传 1 表示不分页，返回全部（用于下拉选择框）
    """
    page = request.args.get("page", 1, type=int)
    size = request.args.get("size", 8, type=int)
    keyword = (request.args.get("keyword") or "").strip()
    category = (request.args.get("category") or "").strip()
    return_all = request.args.get("all", type=int) == 1

    query = KnowledgeBase.query.filter(KnowledgeBase.del_flag == 0)
    if keyword:
        query = query.filter(KnowledgeBase.name.like(f"%{keyword}%"))
    if category:
        query = query.filter(KnowledgeBase.category == category)

    # 统计每个知识库下的文档数量（一次分组查询搞定，避免 N+1 问题）
    count_rows = db.session.query(
        KbDocument.kb_id, func.count(KbDocument.id)
    ).filter(KbDocument.del_flag == 0).group_by(KbDocument.kb_id).all()
    doc_count_map = {kb_id: count for kb_id, count in count_rows}

    if return_all:
        # 不分页模式：返回所有启用的知识库
        records = query.filter(KnowledgeBase.status == 1).order_by(KnowledgeBase.id.asc()).all()
        items = [kb.to_dict(doc_count_map.get(kb.id, 0)) for kb in records]
        return success(data=items)

    pagination = db.paginate(
        query.order_by(KnowledgeBase.id.desc()),
        page=page, per_page=size, error_out=False,
    )
    items = [kb.to_dict(doc_count_map.get(kb.id, 0)) for kb in pagination.items]
    return page_result(items, pagination.total, page, size)


@kb_bp.route("/detail/<int:kb_id>", methods=["GET"])
@login_required
def kb_detail(kb_id: int):
    """
    查询知识库详情

    :param kb_id: 知识库ID
    """
    kb = KnowledgeBase.query.filter_by(id=kb_id, del_flag=0).first()
    if not kb:
        return error("知识库不存在")

    doc_count = KbDocument.query.filter_by(kb_id=kb_id, del_flag=0).count()
    return success(data=kb.to_dict(doc_count))


@kb_bp.route("/categories", methods=["GET"])
@login_required
def kb_categories():
    """
    获取所有已使用的知识库分类（用于前端筛选下拉框）

    :return: ["人事制度", "技术文档", ...]
    """
    rows = db.session.query(KnowledgeBase.category).filter(
        KnowledgeBase.del_flag == 0
    ).distinct().all()
    return success(data=[row[0] for row in rows if row[0]])


@kb_bp.route("/create", methods=["POST"])
@admin_required
def kb_create():
    """
    新建知识库

    请求体：{"name": "xx制度", "description": "描述", "category": "人事制度", "cover_color": "#409EFF"}
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return error("知识库名称不能为空")

    # 名称不允许重复
    if KnowledgeBase.query.filter_by(name=name, del_flag=0).first():
        return error("该知识库名称已存在")

    user = get_current_user()
    kb = KnowledgeBase(
        name=name,
        description=(data.get("description") or "").strip(),
        category=(data.get("category") or "通用").strip(),
        cover_color=data.get("cover_color") or COVER_COLORS[0],
        creator_id=user.id,
        status=1,
    )
    db.session.add(kb)
    db.session.commit()
    return success(data=kb.to_dict(0), message="知识库创建成功")


@kb_bp.route("/update/<int:kb_id>", methods=["PUT"])
@admin_required
def kb_update(kb_id: int):
    """
    修改知识库信息

    :param kb_id: 知识库ID
    """
    kb = KnowledgeBase.query.filter_by(id=kb_id, del_flag=0).first()
    if not kb:
        return error("知识库不存在")

    data = request.get_json(silent=True) or {}

    new_name = (data.get("name") or "").strip()
    if new_name and new_name != kb.name:
        if KnowledgeBase.query.filter_by(name=new_name, del_flag=0).first():
            return error("该知识库名称已存在")
        kb.name = new_name

    if "description" in data:
        kb.description = (data.get("description") or "").strip()
    if "category" in data:
        kb.category = (data.get("category") or "通用").strip()
    if "cover_color" in data:
        kb.cover_color = data.get("cover_color") or kb.cover_color
    if "status" in data:
        kb.status = 1 if data.get("status") == 1 else 0

    db.session.commit()
    return success(data=kb.to_dict(), message="修改成功")


@kb_bp.route("/delete/<int:kb_id>", methods=["DELETE"])
@admin_required
def kb_delete(kb_id: int):
    """
    删除知识库（逻辑删除）

    同时会删除该知识库下的所有文档记录，并清除 Chroma 中对应的 collection。

    :param kb_id: 知识库ID
    """
    kb = KnowledgeBase.query.filter_by(id=kb_id, del_flag=0).first()
    if not kb:
        return error("知识库不存在")

    # 逻辑删除知识库与它下面的文档
    kb.del_flag = 1
    KbDocument.query.filter_by(kb_id=kb_id).update({"del_flag": 1})
    db.session.commit()

    # 删除向量库中的整个 collection（失败不影响主流程）
    delete_collection(kb_id)
    return success(message="知识库已删除")


# ===========================================================================
# 二、文档相关接口
# ===========================================================================

@kb_bp.route("/doc/list", methods=["GET"])
@login_required
def doc_list():
    """
    分页查询文档列表

    查询参数：
        kb_id   按知识库过滤（不传表示全部）
        page    页码
        size    每页条数
        keyword 文件名关键字
        status  处理状态：0待处理 1向量化中 2已完成 3失败
    """
    page = request.args.get("page", 1, type=int)
    size = request.args.get("size", 10, type=int)
    kb_id = request.args.get("kb_id", type=int)
    keyword = (request.args.get("keyword") or "").strip()
    status = request.args.get("status", type=int)

    query = KbDocument.query.filter(KbDocument.del_flag == 0)
    if kb_id:
        query = query.filter(KbDocument.kb_id == kb_id)
    if keyword:
        query = query.filter(KbDocument.file_name.like(f"%{keyword}%"))
    if status is not None:
        query = query.filter(KbDocument.status == status)

    pagination = db.paginate(
        query.order_by(KbDocument.id.desc()),
        page=page, per_page=size, error_out=False,
    )

    # 批量查出知识库名称与上传人昵称，避免逐条查询数据库
    kb_ids = {doc.kb_id for doc in pagination.items}
    user_ids = {doc.uploader_id for doc in pagination.items}
    kb_map = {kb.id: kb.name for kb in KnowledgeBase.query.filter(KnowledgeBase.id.in_(kb_ids)).all()} if kb_ids else {}
    user_map = {u.id: (u.nickname or u.username) for u in SysUser.query.filter(SysUser.id.in_(user_ids)).all()} if user_ids else {}

    items = [
        doc.to_dict(kb_map.get(doc.kb_id), user_map.get(doc.uploader_id))
        for doc in pagination.items
    ]
    return page_result(items, pagination.total, page, size)


@kb_bp.route("/doc/upload", methods=["POST"])
@admin_required
def doc_upload():
    """
    上传文档并自动向量化

    请求格式：multipart/form-data
        kb_id  必填，目标知识库ID
        file   必填，文件对象

    上传成功后文档状态为「待处理(0)」，后台线程会依次完成解析、切分、向量化，
    处理完成后状态变为「已完成(2)」或「失败(3)」。
    """
    kb_id = request.form.get("kb_id", type=int)
    if not kb_id:
        return error("请先选择目标知识库")

    kb = KnowledgeBase.query.filter_by(id=kb_id, del_flag=0).first()
    if not kb:
        return error("知识库不存在")

    file = request.files.get("file")
    if not file or not file.filename:
        return error("请选择要上传的文件")

    # 校验文件后缀
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    if ext not in allowed:
        return error(f"不支持的文件类型，仅支持：{'、'.join(sorted(allowed))}")

    # 文件名安全处理 + 生成唯一存储名（原始文件名保留在数据库中）
    origin_name = _clean_filename(file.filename)
    save_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], str(kb_id))
    os.makedirs(save_dir, exist_ok=True)
    save_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(save_dir, save_name)
    file.save(save_path)

    user = get_current_user()
    doc = KbDocument(
        kb_id=kb_id,
        file_name=origin_name,
        file_path=save_path,
        file_type=ext,
        file_size=os.path.getsize(save_path),
        status=KbDocument.STATUS_PENDING,
        uploader_id=user.id,
    )
    db.session.add(doc)
    db.session.commit()

    # 开启后台线程执行向量化，避免接口长时间阻塞
    app = current_app._get_current_object()
    threading.Thread(
        target=_process_document,
        args=(app, doc.id),
        name=f"doc-vectorize-{doc.id}",
        daemon=True,
    ).start()

    return success(data=doc.to_dict(kb.name, user.nickname), message="上传成功，正在进行向量化处理")


@kb_bp.route("/doc/reindex/<int:doc_id>", methods=["POST"])
@admin_required
def doc_reindex(doc_id: int):
    """
    重新向量化某个文档（向量化失败或更换嵌入模型后使用）

    :param doc_id: 文档ID
    """
    doc = KbDocument.query.filter_by(id=doc_id, del_flag=0).first()
    if not doc:
        return error("文档不存在")
    if not doc.file_path or not os.path.exists(doc.file_path):
        return error("原始文件已丢失，无法重新向量化")

    doc.status = KbDocument.STATUS_PENDING
    doc.error_msg = None
    db.session.commit()

    app = current_app._get_current_object()
    threading.Thread(
        target=_process_document,
        args=(app, doc_id),
        name=f"doc-reindex-{doc_id}",
        daemon=True,
    ).start()
    return success(message="已开始重新向量化")


@kb_bp.route("/doc/delete/<int:doc_id>", methods=["DELETE"])
@admin_required
def doc_delete(doc_id: int):
    """
    删除文档

    会同时删除服务器上的物理文件、数据库记录以及向量库中对应的向量数据。

    :param doc_id: 文档ID
    """
    doc = KbDocument.query.filter_by(id=doc_id, del_flag=0).first()
    if not doc:
        return error("文档不存在")

    # 删除向量数据
    delete_by_doc_id(doc.kb_id, doc.id)

    # 删除物理文件
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError as exc:
            current_app.logger.warning("删除文件失败：%s", exc)

    db.session.delete(doc)
    db.session.commit()
    return success(message="文档已删除")


# ===========================================================================
# 三、内部工具方法
# ===========================================================================

def _clean_filename(filename: str) -> str:
    """
    清洗上传的文件名，去掉路径分隔符等危险字符（保留中文）

    注意：不能直接使用 werkzeug 的 secure_filename，因为它会把中文全部过滤掉。

    :param filename: 原始文件名
    :return: 清洗后的安全文件名
    """
    filename = filename.replace("\\", "/").split("/")[-1]
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', "", filename)
    filename = filename.replace("..", "")
    return filename.strip() or "未命名文件"


def _process_document(app, doc_id: int):
    """
    后台线程：完成文档的解析、切分与向量化

    这是 RAG 离线链路的核心执行过程，因为要调用嵌入模型逐块计算向量，
    耗时较长（几十秒到几分钟），所以放在后台线程中执行。

    :param app: Flask 应用对象（线程中需要手动推入应用上下文）
    :param doc_id: 文档ID
    """
    with app.app_context():
        doc = db.session.get(KbDocument, doc_id)
        if not doc:
            return

        try:
            # 标记为「向量化中」
            doc.status = KbDocument.STATUS_PROCESSING
            doc.error_msg = None
            db.session.commit()

            # 第一步：解析并切分
            chunks = load_and_split(doc.file_path, doc.file_type)
            if not chunks:
                raise ValueError("文档解析后没有任何有效内容")

            # 第二步：写入 Chroma 向量库
            add_documents(doc.kb_id, doc.id, doc.file_name, chunks)

            # 第三步：回写统计信息
            doc.chunk_count = len(chunks)
            doc.char_count = count_chars(chunks)
            doc.status = KbDocument.STATUS_SUCCESS
            db.session.commit()
            app.logger.info("文档向量化完成：%s（%s 个文本块）", doc.file_name, len(chunks))

        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            doc = db.session.get(KbDocument, doc_id)
            if doc:
                doc.status = KbDocument.STATUS_FAILED
                doc.error_msg = str(exc)[:500]
                db.session.commit()
            app.logger.error("文档向量化失败 doc_id=%s：%s", doc_id, exc)
