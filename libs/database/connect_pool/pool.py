import logging
import threading
from queue import Queue, Empty

logger = logging.getLogger('pymysqlpool')

__all__ = ['PoolContainer', 'PoolIsEmptyException', 'PoolIsFullException']


class PoolIsFullException(Exception):
    pass


class PoolIsEmptyException(Exception):
    pass


class PoolContainer(object):

    def __init__(self, max_pool_size):
        self._pool_lock = threading.RLock()
        self._free_items = Queue()
        self._pool_items = set()
        self._max_pool_size = 0
        self.max_pool_size = max_pool_size

    def __repr__(self):
        return '<{0.__class__.__name__} {0.size})>'.format(self)

    def __iter__(self):
        with self._pool_lock:
            return iter(self._pool_items)

    def __contains__(self, item):
        with self._pool_lock:
            return item in self._pool_items

    def __len__(self):
        with self._pool_lock:
            return len(self._pool_items)

    def add(self, item):
        """
        增加一个新连接
        """
        if item is None:
            return None

        """
        拦截重复的连接
        """
        if item in self:
            logger.debug(
                'Duplicate item found "{}", '
                'current size is "{}"'.format(item, self.size))
            return None

        """
        如果当前连接数量超过最大上线，抛出错误
        """
        if self.pool_size >= self.max_pool_size:
            raise PoolIsFullException()

        """
        往空闲的连接队列里放入新连接，并在线程安全的条件下放进连接池里
        """
        self._free_items.put_nowait(item)
        with self._pool_lock:
            self._pool_items.add(item)

        logger.debug(
            'Add item "{!r}",'
            ' current size is "{}"'.format(item, self.size))

    def return_(self, item):
        """
        将使用后的连接放回空闲的队列里
        """
        if item is None:
            return False

        if item not in self:
            logger.error(
                'Current pool dose not contain item: "{}"'.format(item))
            return False

        self._free_items.put_nowait(item)
        logger.debug('Return item "{!r}", current size is "{}"'.format(item, self.size))
        return True

    def get(self, block=True, wait_timeout=60):
        """
        从队列里获取一个连接，如果在指定时间没有获取到，则抛出一个超时错误
        """
        try:
            item = self._free_items.get(block, timeout=wait_timeout)
        except Empty:
            raise PoolIsEmptyException('Cannot find any available item')
        else:
            logger.debug('Get item "{}",'
                         ' current size is "{}"'.format(item, self.size))
            return item

    @property
    def size(self):
        return '<max={}, current={}, free={}>'.format(self.max_pool_size, self.pool_size, self.free_size)

    @property
    def max_pool_size(self):
        return self._max_pool_size

    @max_pool_size.setter
    def max_pool_size(self, value):
        if value > self._max_pool_size:
            self._max_pool_size = value

    @property
    def pool_size(self):
        return len(self)

    @property
    def free_size(self):
        return self._free_items.qsize()
