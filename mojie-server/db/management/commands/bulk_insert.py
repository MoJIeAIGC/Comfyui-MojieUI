from django.core.management.base import BaseCommand
from db.pool import execute_many
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "使用 SQLAlchemy 连接池批量插入数据示例"

    def handle(self, *args, **options):
        try:
            # 示例数据
            data = [
                {"name": "测试1", "age": 25},
                {"name": "测试2", "age": 30},
                {"name": "测试3", "age": 35},
            ]

            # 构建 SQL 语句
            sql = "INSERT INTO test_table (name, age) VALUES (%(name)s, %(age)s)"
            
            # 执行批量插入
            execute_many(sql, data)
            
            self.stdout.write(self.style.SUCCESS("批量插入成功！"))
        except Exception as e:
            logger.error(f"批量插入失败: {str(e)}")
            self.stdout.write(self.style.ERROR(f"批量插入失败: {str(e)}")) 