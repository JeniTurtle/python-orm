import logging
import threading
import contextlib

from pymysql.connections import Connection
from pymysql.cursors import DictCursor, Cursor

from .pool import PoolContainer, PoolIsFullException, PoolIsEmptyException

logger = logging.getLogger('pymysqlpool')

__all__ = ['MySQLConnectionPool']


class NoFreeConnectionFoundError(Exception):
    pass


class PoolBoundaryExceedsError(Exception):
    pass


class MySQLConnectionPool(object):

    def __init__(self, pool_name, host=None, user=None, password="", database=None, port=3306,
                 charset='utf8', use_dict_cursor=True, max_pool_size=30,
                 enable_auto_resize=True, auto_resize_scale=1.5,
                 pool_resize_boundary=48,
                 defer_connect_pool=False, **kwargs):

        """
        初始化连接池.
        :param pool_name: 连接池的队列名.
        :param host: 数据库host
        :param user: 数据库用户名
        :param password: 数据库密码
        :param database: 数据库名
        :param port: 数据库端口
        :param charset: 数据库编码
        :param use_dict_cursor: 是否使用dict游标
        :param max_pool_size: 最大连接数
        :param enable_auto_resize: 是否允许动态更改最大连接数
        :param pool_resize_boundary: 设置数据库允许的最大连接
        :param auto_resize_scale: 连接池动态更改最大比例
        :param kwargs: 其他`pymysql.Connection`配置项
        """
        # 数据库连接配置
        self._host = host
        self._user = user
        self._password = password
        self._database = database
        self._port = port
        self._charset = charset
        self._cursor_class = DictCursor if use_dict_cursor else Cursor
        self._other_kwargs = kwargs

        # 数据库连接池配置
        self._pool_name = pool_name
        self._max_pool_size = max_pool_size if max_pool_size < pool_resize_boundary else pool_resize_boundary
        self._enable_auto_resize = enable_auto_resize
        self._pool_resize_boundary = pool_resize_boundary
        if auto_resize_scale < 1:
            raise ValueError(
                "Invalid scale {}, must be bigger than 1".format(auto_resize_scale))

        self._auto_resize_scale = int(round(auto_resize_scale, 0))
        self._pool_container = PoolContainer(self._max_pool_size)

        self.__safe_lock = threading.RLock()
        self.__is_killed = False
        self.__is_connected = False

        if not defer_connect_pool:
            self.connect()

    def __repr__(self):
        return '<MySQLConnectionPool ' \
               'name={!r}, size={!r}>'.format(self.pool_name, self.size)

    def __del__(self):
        self.close()

    def __iter__(self):
        return iter(self._pool_container)

    @property
    def pool_name(self):
        return self._pool_name

    @property
    def pool_size(self):
        return self._pool_container.pool_size

    @property
    def free_size(self):
        return self._pool_container.free_size

    @property
    def size(self):
        return '<boundary={}, max={}, current={}, free={}>'.format(self._pool_resize_boundary,
                                                                   self._max_pool_size,
                                                                   self.pool_size,
                                                                   self.free_size)

    @contextlib.contextmanager
    def cursor(self, cursor=None):
        with self.connection(True) as conn:
            assert isinstance(conn, Connection)
            cursor = conn.cursor(cursor)

            try:
                yield cursor
            except Exception as err:
                conn.rollback()
                raise err
            finally:
                cursor.close()

    @contextlib.contextmanager
    def connection(self, autocommit=False):
        conn = self.borrow_connection()
        assert isinstance(conn, Connection)
        old_value = conn.get_autocommit()
        conn.autocommit(autocommit)
        try:
            yield conn
        except Exception as err:
            # logger.error(err, exc_info=True)
            raise err
        finally:
            conn.autocommit(old_value)
            self.return_connection(conn)

    def connect(self):
        """
        启动连接池
        """
        if self.__is_connected:
            return

        logger.info('[{}] Connect to connection pool'.format(self))

        test_conn = self._create_connection()
        try:
            test_conn.ping()
        except Exception as err:
            raise err
        else:
            with self.__safe_lock:
                self.__is_connected = True

            self._adjust_connection_pool()
        finally:
            test_conn.close()

    def close(self):
        """
        关闭连接池
        """
        try:
            logger.info('[{}] Close connection pool'.format(self))
        except Exception:
            pass

        with self.__safe_lock:
            if self.__is_killed is True:
                return True

        self._free()

        with self.__safe_lock:
            self.__is_killed = True

    def borrow_connection(self):
        """
        从连接池中获取一个连接
        """
        block = True

        while True:
            conn = self._borrow(block)
            if conn is None:
                block = not self._adjust_connection_pool()
            else:
                return conn

    def _borrow(self, block):
        try:
            connection = self._pool_container.get(block, None)
        except PoolIsEmptyException:
            return None
        else:
            # 检查连接是否还存活
            connection.ping(reconnect=True)
            return connection

    def return_connection(self, connection):
        """
        将使用完连接放回连接池
        """
        return self._pool_container.return_(connection)

    def _adjust_connection_pool(self):
        """
        动态调整连接池大小.
        """
        # 创建几个新连接
        logger.debug('[{}] Adjust connection pool, '
                     'current size is "{}"'.format(self, self.size))

        if self.pool_size >= self._max_pool_size:
            if self._enable_auto_resize:
                self._adjust_max_pool_size()

        try:
            connection = self._create_connection()
        except Exception as err:
            logger.error(err)
            return False
        else:
            try:
                self._pool_container.add(connection)
            except PoolIsFullException:
                logger.debug('[{}] Connection pool is full now'.format(self.pool_name))
                return False
            else:
                return True

    def _adjust_max_pool_size(self):
        with self.__safe_lock:
            self._max_pool_size *= self._auto_resize_scale
            if self._max_pool_size > self._pool_resize_boundary:
                self._max_pool_size = self._pool_resize_boundary
            logger.debug('[{}] Max pool size adjusted to {}'.format(self, self._max_pool_size))
            self._pool_container.max_pool_size = self._max_pool_size

    def _free(self):
        """
        释放所有连接
        """
        for connection in self:
            try:
                connection.close()
            except Exception as err:
                _ = err

    def _create_connection(self):
        """
        创建pymysql连接
        """
        return Connection(host=self._host,
                          user=self._user,
                          password=self._password,
                          database=self._database,
                          port=self._port,
                          charset=self._charset,
                          cursorclass=self._cursor_class,
                          **self._other_kwargs)
