# -*- coding: utf-8 -*-
"""
文档解析与文本切分

完成 RAG 离线链路的前两步：
  1. 解析：把 PDF / Word / TXT / Markdown / CSV 文件读成纯文本
  2. 切分：把长文本切成若干个 500 字左右的小块（chunk）

为什么要切分？
  大模型的上下文长度有限，且检索时整篇文档作为单位太粗糙，
  切成小块后可以精确定位到"文档中的哪一段"回答了问题。
"""
import os
from typing import List

from flask import current_app
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def _get_loader(file_path: str, file_type: str):
    """
    根据文件类型返回对应的 LangChain 文档加载器

    :param file_path: 文件在服务器上的绝对路径
    :param file_type: 文件后缀（小写，不含点），如 pdf、docx
    :return: 文档加载器实例
    :raises ValueError: 不支持的文件类型
    """
    file_type = (file_type or "").lower()

    if file_type == "pdf":
        from langchain_community.document_loaders import PyPDFLoader
        return PyPDFLoader(file_path)

    if file_type in ("docx", "doc"):
        from langchain_community.document_loaders import Docx2txtLoader
        return Docx2txtLoader(file_path)

    if file_type in ("txt", "md"):
        from langchain_community.document_loaders import TextLoader
        # 企业文档大多为 UTF-8 编码；若报编码错误可在此增加 gbk 兜底
        return TextLoader(file_path, encoding="utf-8")

    if file_type == "csv":
        from langchain_community.document_loaders import CSVLoader
        return CSVLoader(file_path, encoding="utf-8")

    raise ValueError(f"暂不支持的文件类型：{file_type}")


def load_and_split(file_path: str, file_type: str = None) -> List[Document]:
    """
    加载文档并切分为文本块

    :param file_path: 文件绝对路径
    :param file_type: 文件后缀，不传则根据文件名自动推断
    :return: 切分后的文本块列表，每个元素是一个 Document 对象
    :raises FileNotFoundError: 文件不存在
    :raises ValueError: 文件类型不支持或内容为空
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在：{file_path}")

    if not file_type:
        file_type = os.path.splitext(file_path)[1].lstrip(".")

    # 第一步：解析成原始文档对象
    loader = _get_loader(file_path, file_type)
    raw_docs = loader.load()

    # 去掉空白页 / 空行，避免产生无意义的向量数据
    raw_docs = [doc for doc in raw_docs if doc.page_content and doc.page_content.strip()]
    if not raw_docs:
        raise ValueError("文档内容为空，无法解析出文本")

    # 第二步：递归字符切分
    # separators 的作用是优先按"段落 -> 换行 -> 句号 -> 逗号 -> 空格"的顺序切，
    # 尽量保证每一块的语义是完整的
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=current_app.config["CHUNK_SIZE"],
        chunk_overlap=current_app.config["CHUNK_OVERLAP"],
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
        length_function=len,
    )
    chunks = splitter.split_documents(raw_docs)

    # 给每个文本块补充页码信息（PDF 加载器会带 page 元数据）
    for chunk in chunks:
        if "page" in chunk.metadata:
            chunk.metadata["page"] = chunk.metadata["page"] + 1  # 页码从 0 开始，转成从 1 开始

    return chunks


def count_chars(chunks: List[Document]) -> int:
    """
    统计所有文本块的总字符数

    :param chunks: 文本块列表
    :return: 总字符数
    """
    return sum(len(chunk.page_content) for chunk in chunks)
