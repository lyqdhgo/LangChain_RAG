# -*- coding: utf-8 -*-
"""
Chroma 向量数据库封装

设计要点：
  1. 一个知识库对应 Chroma 中的一个 collection，命名规则为 `kb_{知识库ID}`，
     从而实现不同知识库之间的数据隔离。
  2. 每个文本块（chunk）的元数据中都会写入 doc_id（所属文档ID）、
     file_name（文件名）、kb_id（知识库ID），方便按文档删除与展示引用来源。
  3. 距离度量使用余弦距离（cosine）：distance = 1 - 余弦相似度，
     取值范围 0~2，值越小表示语义越相近。
"""
import os
from typing import List, Tuple

from flask import current_app
from langchain_chroma import Chroma
from langchain_core.documents import Document

from rag.embeddings import get_embeddings

# 缓存已创建的 Chroma 对象，避免每次请求都重新连接
_store_cache: dict = {}


def _collection_name(kb_id: int) -> str:
    """
    根据知识库ID生成 Chroma 的 collection 名称

    :param kb_id: 知识库ID
    :return: collection 名称，如 kb_1
    """
    return f"kb_{kb_id}"


def get_vector_store(kb_id: int) -> Chroma:
    """
    获取指定知识库对应的向量库对象

    :param kb_id: 知识库ID
    :return: LangChain 的 Chroma 实例
    """
    name = _collection_name(kb_id)
    if name in _store_cache:
        return _store_cache[name]

    persist_dir = current_app.config["CHROMA_DIR"]
    os.makedirs(persist_dir, exist_ok=True)

    store = Chroma(
        collection_name=name,
        embedding_function=get_embeddings(),
        persist_directory=persist_dir,
        # 使用余弦距离作为相似度度量方式
        collection_metadata={"hnsw:space": "cosine"},
    )
    _store_cache[name] = store
    return store


def add_documents(kb_id: int, doc_id: int, file_name: str, chunks: List[Document]) -> int:
    """
    将切分好的文本块写入向量数据库

    该方法会先删除该文档旧的向量数据，再写入新的，
    因此同一份文档重复上传不会产生重复数据（相当于覆盖更新）。

    :param kb_id: 知识库ID
    :param doc_id: 文档ID
    :param file_name: 文件名，作为元数据保存，用于前端展示引用来源
    :param chunks: 切分后的文本块列表
    :return: 实际写入的文本块数量
    """
    store = get_vector_store(kb_id)

    # 先清理该文档的历史向量，保证幂等
    delete_by_doc_id(kb_id, doc_id)

    if not chunks:
        return 0

    # 为每个文本块补充元数据
    for index, chunk in enumerate(chunks):
        chunk.metadata.update({
            "kb_id": kb_id,
            "doc_id": doc_id,
            "file_name": file_name,
            "chunk_index": index,
        })

    ids = [f"kb{kb_id}_doc{doc_id}_{i}" for i in range(len(chunks))]
    store.add_documents(documents=chunks, ids=ids)
    return len(chunks)


def delete_by_doc_id(kb_id: int, doc_id: int) -> int:
    """
    删除某个文档在向量库中的全部文本块

    :param kb_id: 知识库ID
    :param doc_id: 文档ID
    :return: 删除的文本块数量
    """
    store = get_vector_store(kb_id)
    try:
        # 先按元数据条件查出所有主键ID，再按ID批量删除
        result = store.get(where={"doc_id": doc_id})
        ids = result.get("ids") or []
        if ids:
            store.delete(ids=ids)
        return len(ids)
    except Exception as exc:  # noqa: BLE001
        # 向量库中本来就没有该文档时会抛异常，这里吞掉不影响主流程
        current_app.logger.warning("删除向量数据失败 doc_id=%s: %s", doc_id, exc)
        return 0


def delete_collection(kb_id: int) -> bool:
    """
    删除整个知识库对应的 collection（删除知识库时调用）

    :param kb_id: 知识库ID
    :return: 删除成功返回 True
    """
    store = get_vector_store(kb_id)
    try:
        store.delete_collection()
        _store_cache.pop(_collection_name(kb_id), None)
        return True
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning("删除 collection 失败 kb_id=%s: %s", kb_id, exc)
        return False


def similarity_search(kb_ids: List[int], question: str, top_k: int = None,
                      score_threshold: float = None) -> List[Tuple[Document, float]]:
    """
    在指定知识库中做相似度检索

    :param kb_ids: 参与检索的知识库ID列表，为空表示检索所有知识库
    :param question: 用户的问题
    :param top_k: 每个知识库返回的文本块数量，默认读取配置
    :param score_threshold: 余弦距离阈值，距离大于该值的片段会被过滤掉
    :return: [(文本块, 余弦距离), ...] 按距离升序排列（越靠前越相关）
    """
    top_k = top_k or current_app.config["RETRIEVE_TOP_K"]
    if score_threshold is None:
        score_threshold = current_app.config["RETRIEVE_SCORE_THRESHOLD"]

    all_hits: List[Tuple[Document, float]] = []
    for kb_id in kb_ids:
        store = get_vector_store(kb_id)
        try:
            hits = store.similarity_search_with_score(question, k=top_k)
        except Exception as exc:  # noqa: BLE001
            # 某个知识库检索失败不影响其他知识库
            current_app.logger.warning("知识库 %s 检索失败: %s", kb_id, exc)
            continue
        all_hits.extend(hits)

    # 过滤掉距离过大（即相关性太低）的片段
    all_hits = [item for item in all_hits if item[1] <= score_threshold]
    # 跨知识库合并后统一按距离升序排序，并截取前 top_k 条
    all_hits.sort(key=lambda item: item[1])
    return all_hits[:top_k]


def build_sources(hits: List[Tuple[Document, float]]) -> List[dict]:
    """
    把检索结果整理成前端展示用的"引用来源"列表

    :param hits: similarity_search 返回的检索结果
    :return: [{"file_name": "xx.pdf", "kb_id": 1, "chunk_index": 0, "score": 0.92, "content": "..."}]
    """
    sources = []
    seen = set()
    for doc, distance in hits:
        meta = doc.metadata or {}
        file_name = meta.get("file_name", "未知文档")
        # 同一文档只保留相关度最高的一段，避免引用列表重复
        key = (file_name, meta.get("doc_id"))
        if key in seen:
            continue
        seen.add(key)

        # 余弦距离转成相似度百分比：distance 越小，相似度越接近 1
        similarity = round(max(0.0, 1.0 - float(distance)), 4)
        sources.append({
            "file_name": file_name,
            "doc_id": meta.get("doc_id"),
            "kb_id": meta.get("kb_id"),
            "chunk_index": meta.get("chunk_index"),
            "score": similarity,
            "content": doc.page_content[:200],  # 仅返回片段预览
        })
    return sources
