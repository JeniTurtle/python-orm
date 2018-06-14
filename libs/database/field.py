#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Knows'

"""
保存数据库中的表的字段属性

self._order: 实例属性，实例化时从类属性处得到，用于记录该实例是该类的第多少个实例
   例：
       定义user时该类进行了5次实例化，来保存字段属性
           id = IntegerField(primary_key=True)
           name = StringField()
           email = StringField(updatable=False)
           passwd = StringField(default=lambda: '******')
           last_modified = FloatField()
       最后各实例的_order 属性就是这样的
           INFO:root:[TEST _COUNT] name => 1
           INFO:root:[TEST _COUNT] passwd => 3
           INFO:root:[TEST _COUNT] id => 0
           INFO:root:[TEST _COUNT] last_modified => 4
           INFO:root:[TEST _COUNT] email => 2
       最后生成__sql时（见_gen_sql 函数），这些字段就是按序排列
           create table `user` (
               `id` bigint not null,
               `name` varchar(255) not null,
               `email` varchar(255) not null,
               `passwd` varchar(255) not null,
               `last_modified` real not null,
               primary key(`id`)
           );
self._default: 用于让orm自己填入缺省值，缺省值可以是可调用对象，比如函数
           比如：passwd 字段 <StringField:passwd,varchar(255),default(<function <lambda> at 0x0000000002A13898>),UI>
                这里passwd的默认值就可以通过返回的函数调用取得
其他的实例属性都是用来描述字段属性的
"""


class Field(object):

    _count = 0

    """
    sql属性就支持这么多，不够可以添加
    """
    def __init__(self, **kw):
        self.name = kw.get('name', None)
        self._default = kw.get('default', None)
        self.primary_key = kw.get('primary_key', False)
        self.nullable = kw.get('nullable', False)
        self.updatable = kw.get('updatable', True)
        self.insertable = kw.get('insertable', True)
        self.ddl = kw.get('ddl', '')
        """
        不理解_order和_count干嘛用的，看最上面的注释
        """
        self._order = Field._count
        Field._count += 1

    @property
    def default(self):
        """
        利用getter实现的一个写保护的 实例属性
        """
        d = self._default
        return d() if callable(d) else d

    def __str__(self):
        """
        返回实例对象的描述信息，比如：
            <IntegerField:id,bigint,default(0),UI>
            类：实例：实例ddl属性：实例default信息，3中标志位：N U I
        """
        s = ['<%s:%s,%s,default(%s),' % (self.__class__.__name__, self.name, self.ddl, self._default)]
        self.nullable and s.append('N')
        self.updatable and s.append('U')
        self.insertable and s.append('I')
        s.append('>')
        return ''.join(s)


class StringField(Field):
    """
    保存String类型字段的属性
    """
    def __init__(self, **kw):
        if 'default' not in kw:
            kw['default'] = ''
        if 'ddl' not in kw:
            kw['ddl'] = 'varchar(255)'
        super().__init__(**kw)


class IntegerField(Field):
    """
    保存Integer类型字段的属性
    """
    def __init__(self, **kw):
        if 'default' not in kw:
            kw['default'] = 0
        if 'ddl' not in kw:
            kw['ddl'] = 'bigint'
        super().__init__(**kw)


class FloatField(Field):
    """
    保存Float类型字段的属性
    """
    def __init__(self, **kw):
        if 'default' not in kw:
            kw['default'] = 0.0
        if 'ddl' not in kw:
            kw['ddl'] = 'real'
        super().__init__(**kw)


class BooleanField(Field):
    """
    保存BooleanField类型字段的属性
    """
    def __init__(self, **kw):
        if 'default' not in kw:
            kw['default'] = False
        if 'ddl' not in kw:
            kw['ddl'] = 'bool'
        super().__init__(**kw)


class TextField(Field):
    """
    保存Text类型字段的属性
    """
    def __init__(self, **kw):
        if 'default' not in kw:
            kw['default'] = ''
        if 'ddl' not in kw:
            kw['ddl'] = 'text'
        super().__init__(**kw)


class BlobField(Field):
    """
    保存Blob类型字段的属性
    """
    def __init__(self, **kw):
        if 'default' not in kw:
            kw['default'] = ''
        if 'ddl' not in kw:
            kw['ddl'] = 'blob'
        super().__init__(**kw)
