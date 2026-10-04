# -*- coding: utf-8 -*-
"""
统一响应封装

所有接口都返回如下固定结构，前端只需判断 code 是否为 200：
{
    "code": 200,
    "message": "操作成功",
    "data": {...}
}
"""
from flask import jsonify

# 业务状态码常量
CODE_SUCCESS = 200        # 成功
CODE_FAIL = 500           # 业务失败
CODE_UNAUTHORIZED = 401   # 未登录 / 登录已过期
CODE_FORBIDDEN = 403      # 无权限访问
CODE_NOT_FOUND = 404      # 资源不存在


def success(data=None, message: str = "操作成功"):
    """
    返回成功响应

    :param data: 业务数据，可以是字典、列表或 None
    :param message: 提示信息
    :return: Flask 的 JSON 响应对象
    """
    return jsonify({"code": CODE_SUCCESS, "message": message, "data": data})


def error(message: str = "操作失败", code: int = CODE_FAIL, data=None):
    """
    返回失败响应

    注意：这里 HTTP 状态码统一返回 200，业务错误通过 code 字段区分，
    这样前端拦截器可以统一处理，简单直观。

    :param message: 错误提示信息
    :param code: 业务状态码
    :param data: 附加数据
    :return: Flask 的 JSON 响应对象
    """
    return jsonify({"code": code, "message": message, "data": data})


def page_result(items: list, total: int, page: int = 1, size: int = 10, message: str = "查询成功"):
    """
    返回分页结果

    :param items: 当前页的数据列表
    :param total: 总记录数
    :param page: 当前页码，从 1 开始
    :param size: 每页条数
    :param message: 提示信息
    :return: Flask 的 JSON 响应对象
    """
    return success(
        data={"list": items, "total": total, "page": page, "size": size},
        message=message,
    )
