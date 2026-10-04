# -*- coding: utf-8 -*-
"""
RAG（检索增强生成）核心包

整个 RAG 流程分为两条链路：

【离线链路：文档入库】
    上传文件 -> 解析文本(loader) -> 切分成小块(splitter) -> 调用嵌入模型转向量 -> 存入 Chroma

【在线链路：智能问答】
    用户提问 -> 问题向量化 -> Chroma 相似度检索 TopK 文本块
             -> 拼装成 Prompt -> 交给 qwen3:8b 生成回答 -> 返回答案 + 引用来源

包内模块说明：
    embeddings.py      ：Ollama 嵌入模型（把文本转成向量）
    vector_store.py    ：Chroma 向量数据库的增删查封装
    document_loader.py ：文档解析与文本切分
    qa_chain.py        ：检索 + 提示词 + 大模型的问答链
"""
from rag.embeddings import get_embeddings, check_ollama_status
from rag.vector_store import (
    add_documents,
    delete_by_doc_id,
    delete_collection,
    similarity_search,
)
from rag.document_loader import load_and_split
from rag.qa_chain import RagQaService, get_rag_service

__all__ = [
    "get_embeddings",
    "check_ollama_status",
    "add_documents",
    "delete_by_doc_id",
    "delete_collection",
    "similarity_search",
    "load_and_split",
    "RagQaService",
    "get_rag_service",
]
