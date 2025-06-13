from django.db import close_old_connections, transaction
from .db_utils import close_all_connections
import logging

logger = logging.getLogger(__name__)

class DatabaseConnectionMiddleware:
    """
    数据库连接管理中间件
    确保每个请求结束后关闭数据库连接，并处理事务错误
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            # 如果发生异常，确保回滚任何未完成的事务
            if transaction.get_connection().in_atomic_block:
                transaction.set_rollback(True)
                logger.warning(f"Transaction rolled back due to error: {str(e)}")
            raise
        finally:
            # 请求结束后关闭所有数据库连接
            try:
                close_all_connections()
            except Exception as e:
                logger.error(f"Error closing database connections: {str(e)}")