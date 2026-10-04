# -*- coding: utf-8 -*-
"""
RAG 问答链（本项目最核心的模块）

完整流程：
    用户问题
      ↓
    在 Chroma 中做相似度检索，拿到 TopK 个相关文本块   ← 检索（Retrieval）
      ↓
    把文本块拼成【参考资料】，和历史对话一起塞进 Prompt   ← 增强（Augmented）
      ↓
    交给 qwen3:8b 生成回答                              ← 生成（Generation）

本模块同时提供两种调用方式：
    ask()    ：一次性返回完整答案（普通接口）
    stream() ：边生成边返回（SSE 流式接口，前端打字机效果，体验更好）
"""
import time
from typing import Iterator, List, Optional

from flask import current_app
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama

from rag.vector_store import build_sources, similarity_search

# ---------------------------------------------------------------------------
# 提示词模板
# ---------------------------------------------------------------------------

# 系统提示词：约束大模型的行为，这是保证 RAG 回答质量的关键
SYSTEM_PROMPT = """你是「企业知识库智能助手」，负责根据公司内部知识库资料回答员工的提问。

你必须严格遵守以下规则：
1. 只能依据【参考资料】中的内容作答，绝对禁止编造资料之外的信息。
2. 如果【参考资料】中没有相关信息，直接回答："抱歉，知识库中暂未找到相关内容，建议联系管理员补充资料。"，不要强行回答。
3. 回答要条理清晰；涉及流程、步骤时使用 1. 2. 3. 的序号列出。
4. 涉及数字、金额、天数、比例等关键信息，必须与参考资料完全一致。
5. 使用简体中文回答，语气专业、简洁，不要重复用户的问题。
6. 禁止输出你的思考过程，直接给出最终答案。

/no_think"""

# 用户提示词模板：{context} 是检索到的资料，{question} 是用户的问题
HUMAN_PROMPT = """请根据下面的参考资料回答我的问题。

【参考资料】
{context}

【我的问题】
{question}"""

# 检索不到任何资料时的兜底回答
NO_RESULT_ANSWER = "抱歉，知识库中暂未找到相关内容，建议联系管理员补充资料。"

# 参与多轮对话的历史消息条数上限（太多会挤占上下文长度）
MAX_HISTORY_MESSAGES = 6


class RagQaService:
    """
    RAG 问答服务类

    对外提供两个方法：
      - ask()    ：同步问答，返回 {"answer": 答案, "sources": 引用来源, "elapsed": 耗时}
      - stream() ：流式问答，逐段吐出结果，供前端做打字机效果

    大模型对象与提示词链都是懒加载的（第一次使用时才创建），
    这样可以加快 Flask 的启动速度。
    """

    def __init__(self):
        """初始化服务，大模型与链对象延迟到真正使用时再创建"""
        self._llm: Optional[ChatOllama] = None
        self._prompt: Optional[ChatPromptTemplate] = None
        self._chain = None

    # ------------------------------------------------------------------
    # 一、懒加载的模型与链对象
    # ------------------------------------------------------------------
    @property
    def llm(self) -> ChatOllama:
        """
        获取 Ollama 对话大模型对象（单例）

        :return: ChatOllama 实例
        """
        if self._llm is None:
            self._llm = ChatOllama(
                model=current_app.config["LLM_MODEL"],
                base_url=current_app.config["OLLAMA_BASE_URL"],
                temperature=current_app.config["LLM_TEMPERATURE"],
                # 上下文窗口设为 8192，足以容纳参考资料 + 多轮历史 + 回答
                num_ctx=8192,
            )
        return self._llm

    @property
    def prompt(self) -> ChatPromptTemplate:
        """
        构建提示词模板（系统提示 + 历史对话 + 当前问题）

        :return: ChatPromptTemplate 实例
        """
        if self._prompt is None:
            self._prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                # 历史对话占位符，做多轮问答时把之前的消息按顺序填进来
                MessagesPlaceholder(variable_name="history", optional=True),
                ("human", HUMAN_PROMPT),
            ])
        return self._prompt

    @property
    def chain(self):
        """
        构建 LangChain 的 LCEL 处理链：提示词 → 大模型 → 字符串解析

        这是 LangChain 表达式语言（LCEL）的经典写法，用 `|` 把组件串起来，
        数据会像流水线一样依次经过每个组件。

        :return: 可调用的 Runnable 链对象
        """
        if self._chain is None:
            self._chain = self.prompt | self.llm | StrOutputParser()
        return self._chain

    # ------------------------------------------------------------------
    # 二、检索与上下文拼装
    # ------------------------------------------------------------------
    def retrieve(self, question: str, kb_ids: List[int], top_k: int = None) -> list:
        """
        从向量库中检索与问题相关的文本块

        :param question: 用户问题
        :param kb_ids: 参与检索的知识库ID列表
        :param top_k: 返回的文本块数量
        :return: [(Document, 距离), ...]
        """
        if not kb_ids:
            return []
        return similarity_search(kb_ids, question, top_k=top_k)

    @staticmethod
    def format_context(hits: list) -> str:
        """
        把检索到的文本块拼装成提示词中的【参考资料】

        每一段都带上序号和来源文件名，方便大模型在回答时引用。

        :param hits: retrieve() 返回的检索结果
        :return: 拼接好的参考资料字符串
        """
        if not hits:
            return "（无）"

        parts = []
        for index, (doc, _distance) in enumerate(hits, start=1):
            file_name = (doc.metadata or {}).get("file_name", "未知文档")
            content = doc.page_content.strip()
            parts.append(f"[资料{index}] 来源：{file_name}\n{content}")
        return "\n\n".join(parts)

    @staticmethod
    def build_history(records: list) -> list:
        """
        把数据库中的历史消息转换成 LangChain 的消息对象

        :param records: ChatMessage 对象列表（按时间正序）
        :return: [HumanMessage / AIMessage, ...]
        """
        from langchain_core.messages import AIMessage, HumanMessage

        messages = []
        for record in records[-MAX_HISTORY_MESSAGES:]:
            if record.role == "user":
                messages.append(HumanMessage(content=record.content or ""))
            else:
                messages.append(AIMessage(content=record.content or ""))
        return messages

    # ------------------------------------------------------------------
    # 三、对外问答方法
    # ------------------------------------------------------------------
    def ask(self, question: str, kb_ids: List[int], history: list = None) -> dict:
        """
        同步问答：一次性拿到完整答案

        :param question: 用户问题
        :param kb_ids: 参与检索的知识库ID列表
        :param history: 历史消息对象列表，用于多轮对话
        :return: {"answer": 回答内容, "sources": 引用来源列表, "elapsed": 耗时毫秒}
        """
        start = time.time()

        # 第一步：检索
        hits = self.retrieve(question, kb_ids)
        sources = build_sources(hits)

        # 第二步：检索不到资料时直接返回兜底话术，不再调用大模型（省时省算力）
        if not hits:
            return {
                "answer": NO_RESULT_ANSWER,
                "sources": [],
                "elapsed": int((time.time() - start) * 1000),
            }

        # 第三步：拼装提示词并调用大模型
        answer = self.chain.invoke({
            "history": history or [],
            "context": self.format_context(hits),
            "question": question,
        })

        return {
            "answer": (answer or "").strip(),
            "sources": sources,
            "elapsed": int((time.time() - start) * 1000),
        }

    def stream(self, question: str, kb_ids: List[int], history: list = None) -> Iterator[dict]:
        """
        流式问答：边生成边返回，前端可实现打字机效果

        生成器依次产出三种事件：
          {"type": "sources", "data": [...]}   —— 先推送引用来源
          {"type": "message", "data": "文本"}  —— 再逐段推送回答内容
          {"type": "done",    "data": {...}}   —— 最后推送耗时等结束信息

        :param question: 用户问题
        :param kb_ids: 参与检索的知识库ID列表
        :param history: 历史消息对象列表
        :return: 事件字典生成器
        """
        start = time.time()

        # 第一步：检索，并把来源先发给前端
        hits = self.retrieve(question, kb_ids)
        sources = build_sources(hits)
        yield {"type": "sources", "data": sources}

        # 第二步：没有检索到资料，直接返回兜底话术
        if not hits:
            yield {"type": "message", "data": NO_RESULT_ANSWER}
            yield {"type": "done", "data": {"elapsed": int((time.time() - start) * 1000)}}
            return

        # 第三步：流式调用大模型，逐段吐出回答
        full_answer = []
        try:
            for piece in self.chain.stream({
                "history": history or [],
                "context": self.format_context(hits),
                "question": question,
            }):
                if piece:
                    full_answer.append(piece)
                    yield {"type": "message", "data": piece}
        except Exception as exc:  # noqa: BLE001
            # 模型调用失败时，把错误信息也通过流返回给前端，避免前端一直转圈
            current_app.logger.error("大模型调用失败: %s", exc)
            tip = f"\n\n[生成中断] 调用大模型失败：{exc}"
            yield {"type": "message", "data": tip}
            full_answer.append(tip)

        yield {
            "type": "done",
            "data": {
                "elapsed": int((time.time() - start) * 1000),
                "answer": "".join(full_answer).strip(),
            },
        }


# 模块级单例，避免每次请求都重新创建服务对象
_rag_service: Optional[RagQaService] = None


def get_rag_service() -> RagQaService:
    """
    获取全局唯一的 RAG 问答服务对象

    :return: RagQaService 实例
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = RagQaService()
    return _rag_service
