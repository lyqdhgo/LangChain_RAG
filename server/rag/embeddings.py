# -*- coding: utf-8 -*-
"""
嵌入模型（Embedding）封装

作用：把一段文本转换成一串固定长度的浮点数（向量），
     语义相近的文本，其向量在空间中的距离也更近，
     这是向量检索能够"按意思找内容"的根本原理。

本项目使用 Ollama 提供的 qwen3-embedding:4b 模型，
使用前需要先执行：ollama pull qwen3-embedding:4b
"""
import json
import urllib.error
import urllib.request

from flask import current_app
from langchain_ollama import OllamaEmbeddings

# 模块级缓存：嵌入模型对象比较重，全局只创建一次即可
_embeddings_instance = None


def get_embeddings() -> OllamaEmbeddings:
    """
    获取全局唯一的嵌入模型对象（单例）

    :return: 配置好的 OllamaEmbeddings 实例
    """
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = OllamaEmbeddings(
            model=current_app.config["EMBEDDING_MODEL"],
            base_url=current_app.config["OLLAMA_BASE_URL"],
        )
    return _embeddings_instance


def check_ollama_status() -> dict:
    """
    检查 Ollama 服务是否可用，以及所需模型是否已下载

    通过调用 Ollama 的 /api/tags 接口获取本地已安装的模型列表。

    :return: {"online": 是否在线, "models": 已安装模型名列表, "missing": 缺失的模型列表}
    """
    base_url = current_app.config["OLLAMA_BASE_URL"].rstrip("/")
    result = {"online": False, "models": [], "missing": []}

    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=3) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        # Ollama 返回结构：{"models": [{"name": "qwen3:8b", ...}, ...]}
        models = [item.get("name", "") for item in body.get("models", [])]
        result["online"] = True
        result["models"] = models

        # 检查所需模型是否都已安装（忽略 :latest 之类的标签差异）
        need = [current_app.config["LLM_MODEL"], current_app.config["EMBEDDING_MODEL"]]
        for model in need:
            if not any(m == model or m.startswith(model.split(":")[0] + ":") for m in models):
                result["missing"].append(model)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        # Ollama 未启动时直接返回离线状态
        result["online"] = False

    return result
