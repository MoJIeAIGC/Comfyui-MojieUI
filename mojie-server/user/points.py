"""
积分管理模块
提供管理用户积分的工具，包括积分消费、记录等功能
"""
import logging
from django.db import transaction
from django.utils import timezone
from django.db.models import F
from user.models import SysUser

logger = logging.getLogger(__name__)

class PointsManager:
    """
    积分管理器
    处理用户积分的各种操作，包括扣除、添加、查询等
    """
    
    @staticmethod
    def get_user_points(user):
        """
        获取用户积分信息
        :param user: 用户对象
        :return: 积分信息字典
        """
        try:
            if not user:
                return {
                    'success': False,
                    'message': '用户不存在',
                    'data': None
                }
            
            # 查询最新的用户积分
            user = SysUser.objects.get(id=user.id)
            
            # 返回积分信息
            return {
                'success': True,
                'message': '获取积分信息成功',
                'data': {
                    'total_points': user.points,
                    'user_id': user.id,
                    'username': user.username
                }
            }
        except SysUser.DoesNotExist:
            return {
                'success': False,
                'message': '用户不存在',
                'data': None
            }
        except Exception as e:
            logger.error(f"获取用户积分失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取积分信息失败: {str(e)}',
                'data': None
            }
    
    @staticmethod
    def deduct_points(user, points, reason='系统扣除', notes=None, transaction_type='消费'):
        """
        扣除用户积分
        :param user: 用户对象
        :param points: 扣除的积分数量(正整数)
        :param reason: 扣除原因
        :param notes: 详细说明
        :param transaction_type: 交易类型
        :return: 操作结果
        """
        try:
            if not user:
                return {
                    'success': False,
                    'message': '用户不存在',
                    'data': None
                }
            
            # 验证积分值
            try:
                points = int(points)
                if points <= 0:
                    return {
                        'success': False,
                        'message': '扣除的积分必须为正数',
                        'data': None
                    }
            except (ValueError, TypeError):
                return {
                    'success': False,
                    'message': '无效的积分值',
                    'data': None
                }
            
            # 使用事务确保数据一致性
            with transaction.atomic():
                # 获取最新的用户信息
                user = SysUser.objects.select_for_update().get(id=user.id)
                
                # 检查用户积分是否足够
                if user.points < points:
                    return {
                        'success': False,
                        'message': '用户积分不足',
                        'data': {
                            'current_points': user.points,
                            'required_points': points
                        }
                    }
                
                # 扣除积分
                user.points = F('points') - points
                user.save(update_fields=['points'])
                
                # 记录积分变动
                try:
                    # 如果有PointsRecord模型，记录积分变动
                    from user.models import PointsRecord
                    
                    PointsRecord.objects.create(
                        user=user,
                        points_change=-points,  # 使用负数表示扣除
                        balance=user.points,
                        transaction_type=transaction_type,
                        reason=reason,
                        notes=notes or reason,
                        created_at=timezone.now()
                    )
                except ImportError:
                    # 如果没有积分记录模型，只记录日志
                    logger.info(f"用户 {user.username}(ID:{user.id}) 积分扣除: {points}，原因: {reason}")
                
                # 获取更新后的用户积分
                updated_user = SysUser.objects.get(id=user.id)
                
                return {
                    'success': True,
                    'message': '积分扣除成功',
                    'data': {
                        'previous_points': user.points + points,
                        'current_points': updated_user.points,
                        'deducted_points': points
                    }
                }
                
        except SysUser.DoesNotExist:
            return {
                'success': False,
                'message': '用户不存在',
                'data': None
            }
        except Exception as e:
            logger.error(f"扣除用户积分失败: {str(e)}")
            return {
                'success': False,
                'message': f'积分扣除失败: {str(e)}',
                'data': None
            }
    
    @staticmethod
    def add_points(user, points, reason='系统奖励', notes=None, transaction_type='奖励'):
        """
        增加用户积分
        :param user: 用户对象
        :param points: 增加的积分数量(正整数)
        :param reason: 增加原因
        :param notes: 详细说明
        :param transaction_type: 交易类型
        :return: 操作结果
        """
        try:
            if not user:
                return {
                    'success': False,
                    'message': '用户不存在',
                    'data': None
                }
            
            # 验证积分值
            try:
                points = int(points)
                if points <= 0:
                    return {
                        'success': False,
                        'message': '增加的积分必须为正数',
                        'data': None
                    }
            except (ValueError, TypeError):
                return {
                    'success': False,
                    'message': '无效的积分值',
                    'data': None
                }
            
            # 使用事务确保数据一致性
            with transaction.atomic():
                # 获取最新的用户信息
                user = SysUser.objects.select_for_update().get(id=user.id)
                
                # 添加积分
                original_points = user.points
                user.points = F('points') + points
                user.save(update_fields=['points'])
                
                # 记录积分变动
                try:
                    # 如果有PointsRecord模型，记录积分变动
                    from user.models import PointsRecord
                    
                    PointsRecord.objects.create(
                        user=user,
                        points_change=points,  # 正数表示增加
                        balance=user.points,
                        transaction_type=transaction_type,
                        reason=reason,
                        notes=notes or reason,
                        created_at=timezone.now()
                    )
                except ImportError:
                    # 如果没有积分记录模型，只记录日志
                    logger.info(f"用户 {user.username}(ID:{user.id}) 积分增加: {points}，原因: {reason}")
                
                # 获取更新后的用户积分
                updated_user = SysUser.objects.get(id=user.id)
                
                return {
                    'success': True,
                    'message': '积分增加成功',
                    'data': {
                        'previous_points': original_points,
                        'current_points': updated_user.points,
                        'added_points': points
                    }
                }
                
        except SysUser.DoesNotExist:
            return {
                'success': False,
                'message': '用户不存在',
                'data': None
            }
        except Exception as e:
            logger.error(f"增加用户积分失败: {str(e)}")
            return {
                'success': False,
                'message': f'积分增加失败: {str(e)}',
                'data': None
            }
            
    @staticmethod
    def check_points_sufficient(user, required_points):
        """
        检查用户积分是否足够
        :param user: 用户对象
        :param required_points: 需要的积分数量
        :return: 是否足够
        """
        try:
            if not user:
                return False
                
            # 获取最新用户数据
            user = SysUser.objects.get(id=user.id)
            
            # 检查积分是否足够
            return user.points >= required_points
            
        except Exception as e:
            logger.error(f"检查用户积分是否足够失败: {str(e)}")
            return False 