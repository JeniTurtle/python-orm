#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Knows'

from .connect_pool import ConnectionPool


class _Engine(object):
    """
    数据库引擎对象
    用于保存 db模块的核心函数：create_engine 创建出来的数据库连接
    """

    def __init__(self, connect):
        self._connect = connect

    def connect(self):
        return self._connect()


def create_engine(**kw):
    """
    db模型的核心函数，用于连接数据库, 生成全局对象engine，
    engine对象持有数据库连接
    """
    defaults = dict(use_unicode=True, charset='utf8', autocommit=False)
    defaults.update(kw)
    engine = _Engine(lambda: ConnectionPool(**defaults))
    return engine
