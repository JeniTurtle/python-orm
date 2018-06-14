#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Knows'

import functools
import time
import logging


def sql_profiling_decorator(func):
    """
    用来分析sql的执行时间
    """

    @functools.wraps(func)
    def _wrapper(*args, **kw):
        start = time.time()
        t = time.time() - start
        try:
            ret = func(*args, **kw)

        except Exception:
            log_info = 'SQL: Execute Failed! %s, ARGS: %s; Execution time: %sms' % (args[1], args[2:], t)
            logging.warning(log_info)
            raise Exception
        else:
            log_info = 'SQL: %s, ARGS: %s; Execution time: %sms' % (args[1], args[2:], t)
            if t > 0.1:
                logging.warning(log_info)
            else:
                logging.info(log_info)
            return ret

    return _wrapper
