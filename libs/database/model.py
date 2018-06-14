#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Knows'

"""
对类对象动态完成以下操作
避免修改Model类：
    1. 排除对Model类的修改
    2. 从类的属性字典中提取出类属性和字段类 的mapping
    3. 提取完成后移除这些类属性，避免和实例属性冲突
    4. 新增"__mappings__" 属性，保存提取出来的mapping数据
    5. 新增"__table__"属性，保存提取出来的表名
"""

import logging
from .field import Field
from . import db


class ModelMetaclass(type):

    __defaultFields = frozenset(['insert_time', 'update_time'])

    def __new__(mcs, model_name, bases, attrs):
        # 跳过Model类:
        if model_name == 'Mode':
            return type.__new__(mcs, model_name, bases, attrs)

        # 记录所有Model子类名称:
        if not hasattr(mcs, 'subclasses'):
            mcs.subclasses = {}
        if model_name not in mcs.subclasses:
            mcs.subclasses[model_name] = model_name
        else:
            logging.warning('Redefine class: %s' % model_name)

        logging.info('Scan ORMapping %s...' % model_name)

        mappings = dict()
        primary_key = None

        for k, v in attrs.items():
            if isinstance(v, Field):
                # 如果Field没有定义name属性，则把传入的key当做字段名
                if not v.name:
                    v.name = k
                logging.info('[MAPPING] Found mapping: %s => %s' % (k, v))

                # 检查索引相关配置:
                if v.primary_key:
                    if primary_key:
                        raise TypeError('Cannot define more than 1 primary key in class: %s' % model_name)
                    if v.updatable:
                        logging.warning('NOTE: change primary key to non-updatable.')
                        v.updatable = False
                    if v.nullable:
                        logging.warning('NOTE: change primary key to non-nullable.')
                        v.nullable = False
                    primary_key = v
                mappings[k] = v

        # 判断model是否定义主键
        if not primary_key:
            raise TypeError('Primary key not defined in class: %s' % model_name)

        # 把字段都存储到mappings之后，把attrs中的类属性都删除掉，避免跟实例的属性冲突
        for k in mappings.keys():
            attrs.pop(k)

        # 如果model类中没定义__table__属性，就把model名做为table name
        if '__table__' not in attrs:
            attrs['__table__'] = model_name.lower()

        attrs['__mappings__'] = mappings
        attrs['__primary_key__'] = primary_key

        # 如果model子类没有设置__timestamp_field__字段为False，那么就自动增加insert_time和update_time两个字段
        if '__timestamp_field__' in attrs and not attrs['__timestamp_field__']:
                if mcs.__defaultFields not in attrs:
                    attrs[mcs.__defaultFields] = None
        return type.__new__(mcs, model_name, bases, attrs)


class Model(dict, mateclass=ModelMetaclass):
    """
    这是一个基类，用户在子类中 定义映射关系， 因此我们需要动态扫描子类属性 ，
    从中抽取出类属性， 完成 类 <==> 表 的映射， 这里使用 metaclass 来实现。
    最后将扫描出来的结果保存在成类属性
        "__table__" : 表名
        "__mappings__": 字段对象(字段的所有属性，见Field类)
        "__primary_key__": 主键字段
        "__timestamp_field__": 默认为true，设置是否自动增加update_time和insert_time字段
    子类在实例化时，需要完成 实例属性 <==> 行值 的映射， 这里使用 定制dict 来实现。
        Model 从字典继承而来，并且通过"__getattr__","__setattr__"将Model重写，
        使得其像javascript中的 object对象那样，可以通过属性访问 值比如 a.key = value
    """

    def __init__(self, **kw):
        super().__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    @classmethod
    def get(cls, primary_key):
        """
        Get by primary key.
        """
        d = db.select_one('select * from %s where %s=?' % (cls.__table__, cls.__primary_key__.name), primary_key)
        return cls(**d) if d else None

    @classmethod
    def find_first(cls, where, *args):
        """
        通过where语句进行条件查询，返回1个查询结果。如果有多个查询结果
        仅取第一个，如果没有结果，则返回None
        """
        d = db.select_one('select * from %s %s' % (cls.__table__, where), *args)
        return cls(**d) if d else None

    @classmethod
    def find_all(cls, *args):
        """
        查询所有字段， 将结果以一个列表返回
        """
        ret = db.select('select * from `%s`' % cls.__table__)
        return [cls(**d) for d in ret]

    @classmethod
    def find_by(cls, where, *args):
        """
        通过where语句进行条件查询，将结果以一个列表返回
        """
        ret = db.select('select * from `%s` %s' % (cls.__table__, where), *args)
        return [cls(**d) for d in ret]

    @classmethod
    def select_by(cls, where, condition=[], fields=[]):
        """
        通过where语句进行条件查询，将结果以一个列表返回
        """
        fields = ','.join(fields) if fields else '*'
        ret = db.select('select %s from `%s` %s' % (fields, cls.__table__, where), *condition)
        return [cls(**d) for d in ret]

    @classmethod
    def join_by(cls, source_list, source_field, target_field, where=''):
        """
        遍历list，拿到field字段，然后批量查询
        """
        if not source_list:
            return []

        l = []
        for d in source_list:
            l.append("'%s'" % d[source_field])
        where_in_condition = ','.join(l)

        if where:
            where = '%s and %s in (%s)' % (where, target_field, where_in_condition)
        else:
            where = 'where %s in (%s)' % (target_field, where_in_condition)
        ret = db.select('select * from `%s` %s' % (cls.__table__, where))

        for d in source_list:
            d[cls.__table__] = None

            for x in ret:
                if x[target_field] == d[source_field]:
                    d[cls.__table__] = x

        return [cls(**d) for d in source_list]

    @classmethod
    def count_all(cls):
        """
        执行 select count(pk) from table语句，返回一个数值
        """
        return db.select_int('select count(`%s`) from `%s`' % (cls.__primary_key__.name, cls.__table__))

    @classmethod
    def count_by(cls, where, *args):
        """
        通过select count(pk) from table where ...语句进行查询， 返回一个数值
        """
        return db.select_int('select count(`%s`) from `%s` %s' % (cls.__primary_key__.name, cls.__table__, where), *args)

    @classmethod
    def count_by_field(cls, where, field, *args):
        """
        通过select count(field) from table where ...语句进行查询， 返回一个数值
        """
        return db.select_int('select count(%s) from `%s` %s' % (field, cls.__table__, where), *args)

    def update(self):
        """
        如果该行的字段属性有 updatable，代表该字段可以被更新
        用于定义的表（继承Model的类）是一个 Dict对象，键值会变成实例的属性
        所以可以通过属性来判断 用户是否定义了该字段的值
            如果有属性， 就使用用户传入的值
            如果无属性， 则调用字段对象的 default属性传入
            具体见 Field类 的 default 属性
        通过的db对象的update接口执行SQL
            SQL: update `user` set `passwd`=%s,`last_modified`=%s,`name`=%s where id=%s,
                 ARGS: (u'******', 1441878476.202391, u'Michael', 10190
        """
        self.pre_update and self.pre_update()
        L = []
        args = []
        for k, v in self.__mappings__.iteritems():
            if v.updatable:
                if hasattr(self, k):
                    arg = getattr(self, k)
                L.append('`%s`=?' % k)
                args.append(arg)
        pk = self.__primary_key__.name
        args.append(getattr(self, pk))
        db.update('update `%s` set %s where %s=?' % (self.__table__, ','.join(L), pk), *args)
        return self

    def update_by(self, where, *params):

        self.pre_update and self.pre_update()
        L = []
        args = []
        for k, v in self.__mappings__.iteritems():
            if v.updatable:
                if hasattr(self, k):
                    arg = getattr(self, k)
                    L.append('`%s`=?' % k)
                    args.append(arg)
        args.extend(params)
        db.update('update `%s` set %s %s' % (self.__table__, ','.join(L), where), *args)
        return self

    def delete(self):
        """
        通过db对象的 update接口 执行SQL
            SQL: delete from `user` where `id`=%s, ARGS: (10190,)
        """
        self.pre_delete and self.pre_delete()
        pk = self.__primary_key__.name
        args = (getattr(self, pk),)
        db.update('delete from `%s` where `%s`=?' % (self.__table__, pk), *args)
        return self

    def insert(self):
        """
        通过db对象的insert接口执行SQL
            SQL: insert into `user` (`passwd`,`last_modified`,`id`,`name`,`email`) values (%s,%s,%s,%s,%s),
            ARGS: ('******', 1441878476.202391, 10190, 'Michael', 'orm@db.org')
        """
        self.pre_insert and self.pre_insert()
        params = {}
        for k, v in self.__mappings__.iteritems():
            if v.insertable:
                if not hasattr(self, k):
                    setattr(self, k, v.default)
                params[v.name] = getattr(self, k)
        db.insert('%s' % self.__table__, **params)
        return self
