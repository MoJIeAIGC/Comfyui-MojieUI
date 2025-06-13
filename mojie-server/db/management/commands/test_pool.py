from django.core.management.base import BaseCommand
from db.pool import get_engine, execute_query
import time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "测试数据库连接池是否正常工作"

    def handle(self, *args, **options):
        try:
            # 获取引擎实例
            engine = get_engine()
            
            # 打印连接池状态
            self.stdout.write("连接池状态：")
            self.stdout.write(f"连接池大小: {engine.pool.size()}")
            self.stdout.write(f"当前连接数: {engine.pool.checkedin()}")
            self.stdout.write(f"使用中的连接数: {engine.pool.checkedout()}")
            
            # 测试连接
            self.stdout.write("\n测试数据库连接...")
            result = execute_query("SELECT 1")
            self.stdout.write(self.style.SUCCESS("数据库连接测试成功！"))
            
            # 测试连接池复用
            self.stdout.write("\n测试连接池复用...")
            start_time = time.time()
            
            # 模拟并发查询
            for i in range(5):
                execute_query("SELECT SLEEP(0.1)")
                
            end_time = time.time()
            duration = end_time - start_time
            
            self.stdout.write(f"5次查询耗时: {duration:.2f}秒")
            self.stdout.write(f"如果耗时接近0.5秒，说明是串行执行")
            self.stdout.write(f"如果耗时接近0.1秒，说明连接池在复用连接")
            
            # 再次打印连接池状态
            self.stdout.write("\n连接池最终状态：")
            self.stdout.write(f"连接池大小: {engine.pool.size()}")
            self.stdout.write(f"当前连接数: {engine.pool.checkedin()}")
            self.stdout.write(f"使用中的连接数: {engine.pool.checkedout()}")
            
        except Exception as e:
            logger.error(f"连接池测试失败: {str(e)}")
            self.stdout.write(self.style.ERROR(f"连接池测试失败: {str(e)}")) 