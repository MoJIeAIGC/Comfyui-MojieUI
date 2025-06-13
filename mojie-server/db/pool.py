from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def get_engine():
    """
    获取 SQLAlchemy 引擎实例，使用连接池
    """
    try:
        engine = create_engine(
            settings.SQLALCHEMY_DATABASE_URL,
            poolclass=QueuePool,
            **settings.SQLALCHEMY_POOL_SETTINGS
        )
        return engine
    except Exception as e:
        logger.error(f"Failed to create SQLAlchemy engine: {str(e)}")
        raise

# 创建全局引擎实例
engine = get_engine()

def get_connection():
    """
    获取数据库连接
    """
    try:
        return engine.connect()
    except Exception as e:
        logger.error(f"Failed to get database connection: {str(e)}")
        raise

def execute_query(query, params=None):
    """
    执行查询并返回结果
    """
    with get_connection() as conn:
        try:
            # 使用 text() 包装 SQL 查询
            result = conn.execute(text(query), params or {})
            return result.fetchall()
        except Exception as e:
            logger.error(f"Failed to execute query: {str(e)}")
            raise

def execute_many(query, params_list):
    """
    批量执行查询
    """
    with get_connection() as conn:
        try:
            # 使用 text() 包装 SQL 查询
            conn.execute(text(query), params_list)
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to execute batch query: {str(e)}")
            raise 