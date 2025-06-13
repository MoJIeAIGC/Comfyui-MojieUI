import logging
from functools import wraps
from django.db import connection, OperationalError, close_old_connections, transaction
import time
from contextlib import contextmanager
from django.conf import settings
from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)

# 添加监控指标
DB_CONNECTION_COUNTER = Counter(
    'db_connection_total',
    'Total number of database connections',
    ['status']
)

DB_CONNECTION_GAUGE = Gauge(
    'db_connection_active',
    'Number of active database connections'
)

@contextmanager
def db_connection_manager():
    """
    数据库连接管理器，确保连接在使用后被正确关闭
    添加连接池监控和自动重连机制
    """
    try:
        # 确保连接是活跃的
        ensure_connection()
        DB_CONNECTION_GAUGE.inc()
        DB_CONNECTION_COUNTER.labels(status='acquired').inc()
        yield
    except Exception as e:
        # 如果发生异常，确保回滚任何未完成的事务
        if transaction.get_connection().in_atomic_block:
            transaction.set_rollback(True)
            logger.warning(f"Transaction rolled back in db_connection_manager: {str(e)}")
        DB_CONNECTION_COUNTER.labels(status='error').inc()
        raise
    finally:
        # 关闭所有旧连接
        try:
            close_old_connections()
            DB_CONNECTION_GAUGE.dec()
            DB_CONNECTION_COUNTER.labels(status='released').inc()
        except Exception as e:
            logger.error(f"Error closing connections in db_connection_manager: {str(e)}")
            DB_CONNECTION_COUNTER.labels(status='close_error').inc()

def with_db_retry(max_retries=3, retry_delay=1):
    """
    装饰器：重试数据库操作并在操作完成后关闭连接
    添加连接池感知的重试机制
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    with db_connection_manager():
                        return func(*args, **kwargs)
                except OperationalError as e:
                    last_error = e
                    if "Server has gone away" in str(e) or "Lost connection" in str(e):
                        if attempt < max_retries - 1:
                            logger.warning(f"Database connection lost (attempt {attempt + 1}/{max_retries}). Retrying...")
                            time.sleep(retry_delay)
                            # 强制关闭所有连接并重新连接
                            close_all_connections()
                            continue
                    raise
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                        time.sleep(retry_delay)
                        continue
                    raise
            raise last_error
        return wrapper
    return decorator

def ensure_connection():
    """
    确保数据库连接是活跃和有效的
    添加连接池健康检查
    """
    try:
        # 关闭所有旧连接
        close_old_connections()
        
        # 尝试执行一个简单的查询来验证连接
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
    except Exception as e:
        logger.error(f"Failed to ensure database connection: {str(e)}")
        # 关闭所有连接并重新连接
        close_old_connections()
        try:
            connection.connect()
        except Exception as conn_error:
            logger.error(f"Failed to reconnect to database: {str(conn_error)}")
            raise

def close_all_connections():
    """
    关闭所有数据库连接
    添加连接池清理功能
    """
    try:
        # 如果存在未完成的事务，先回滚
        if transaction.get_connection().in_atomic_block:
            transaction.set_rollback(True)
            logger.warning("Rolling back incomplete transaction before closing connections")
        
        # 重置连接计数器
        DB_CONNECTION_GAUGE.set(0)

        close_old_connections()
        logger.info("Successfully closed all database connections")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")
        raise 