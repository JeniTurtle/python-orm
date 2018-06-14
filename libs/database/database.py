#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Knows'

from .db_core import DBBase

"""
本来想做成可以级联调用的，比如 user.where(a=1, b=2).find()
先写个low点的
"""


class DB(object):

    def __init__(self, engine):
        self.db_base = DBBase(engine)

    def select_one(self, sql, *args):
        """
        执行SQL 仅返回一个结果
        如果没有结果 返回None
        如果有1个结果，返回一个结果
        如果有多个结果，返回第一个结果
        :param sql: str
        :param args: list
        :return: Dict instance
        """
        return self.db_base.query(sql, True, *args)

    def select(self, sql, *args):
        """
        执行sql 以列表形式返回结果
        :param sql: str
        :param args: list
        :return: Dict instance
        """
        return self.db_base.query(sql, False, *args)

    def execute(self, sql, *args):
        """
        执行sql 语句，返回执行的行数
        :param sql: str
        :param args: list
        :return: int
        """
        return self.db_base.execute(sql, *args)

    def insert(self, table, **kw):
        """
        执行insert语句
        :param table: str
        :param kw: list
        :return: int
        """
        cols, args = zip(*kw.items())
        sql = 'insert into `%s` (%s) values (%s)' % (table, ','.join(['`%s`' % col for col in cols]), ','.join(['?' for i in range(len(cols))]))
        return self.db_base.execute(sql, *args)

    def insert_many(self, table, fields=list(), values=list()):
        """
        执行insert语句
        :param table:
        :param fields:
        :param values:
        :return: int
        """
        sql = 'insert into `%s` (%s) values (%s)' % (table, ','.join(['`%s`' % field for field in fields]), ','.join(['%s' for field in fields]))
        return self.db_base.executemany(sql, values)
