# -*- coding: utf-8 -*-
"""
密码加密工具

按照需求，用户密码使用 MD5 算法加密后存储到数据库。
例如：123456 加密后为 e10adc3949ba59abbe56e057f20f883e

注意：MD5 属于不可逆加密，只能用于"加密后比对"，无法解密还原。
"""
import hashlib


def md5_encrypt(raw_password: str) -> str:
    """
    对明文密码进行 MD5 加密

    :param raw_password: 明文密码
    :return: 32 位小写的 MD5 密文
    """
    if raw_password is None:
        raw_password = ""
    md5 = hashlib.md5()
    # 必须编码为 bytes 才能参与计算，统一使用 utf-8
    md5.update(raw_password.encode("utf-8"))
    return md5.hexdigest()


def verify_password(raw_password: str, encrypted_password: str) -> bool:
    """
    校验明文密码与数据库中的密文是否匹配

    :param raw_password: 用户输入的明文密码
    :param encrypted_password: 数据库中存储的 MD5 密文
    :return: 匹配返回 True，否则返回 False
    """
    if not encrypted_password:
        return False
    return md5_encrypt(raw_password) == encrypted_password.lower()


# 便于自测：直接运行本文件时会输出 123456 的 MD5 值
if __name__ == "__main__":
    print("123456 的 MD5 值为：", md5_encrypt("123456"))
