#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Knows'

import logging

from libs.classes.dict_class import Dict
from utils.decorator import sql_profiling_decorator

logger = logging.getLogger('pymysql')


class DBBase(object):
    def __init__(self, db_engine):
        self.engine = db_engine
        self.connection = db_engine.connect()

    @property
    def cursor_builder(self):
        return self.connection.cursor

    @sql_profiling_decorator
    def query(self, sql, first, *args):
        """
        执行SQL，返回一个结果 或者多个结果组成的列表
        :param sql: str
        :param first: boolean
        :param args: list
        :return: Dict instance
        """
        names = []
        sql = sql.replace('?', '%s')

        with self.cursor_builder() as cursor:
            cursor.execute(sql, args)
            if cursor.description:
                names = [x[0] for x in cursor.description]
            if first:
                values = cursor.fetchone()
                if not values:
                    return None
                return Dict(names, values)
            return [Dict(names, x) for x in cursor.fetchall()]

    @sql_profiling_decorator
    def execute(self, sql, *args):
        """
        执行update 语句，返回update的行数
        :param sql: str
        :param args: list
        :return: int
        """
        sql = sql.replace('?', '%s')

        with self.cursor_builder() as cursor:
            cursor.execute(sql, args)
            r = cursor.rowcount
            return r

    @sql_profiling_decorator
    def executemany(self, sql, *args):
        """
        执行update 语句，返回update的行数
        :param sql: str
        :param args: list
        :return: int
        """
        sql = sql.replace('?', '%s')

        with self.cursor_builder() as cursor:
            ret = cursor.executemany(sql, *args)
            return ret


