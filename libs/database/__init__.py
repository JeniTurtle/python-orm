#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Knows'

from .db_engine import create_engine
from .db_core import DBBase
from .database import DB

db = None


def db_init(**kw):
    global db

    if db is None:
        engine = create_engine(**kw)
        db = DB(engine)

    return db






