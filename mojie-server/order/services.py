      
from _pydecimal import Decimal
from datetime import timedelta
import json
import configparser
import time
import uuid

from django.db import transaction
from django.utils import timezone
from wechatpayv3 import WeChatPayType, WeChatPay

from alipayOnly.client import AlipayClient
from bankpay.client import BankPayClient
from wechatpay.client import WeChatPayClient
from .models import Order, Payment, Refund, UserVIP
from django.conf import settings


import logging

logger = logging.getLogger(__name__)

class OrderService:
    """
    订单服务类
    提供创建订单和支付记录的功能
    """
    @staticmethod
    def create_order(user, product, amount=None):
        """
        创建订单
        :param user: 用户对象
        :param product: 商品对象
        :param amount: 自定义金额（可选）
        :return: 创建的订单对象
        """
        # 生成订单号
        order_no = f"ORDER_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # 确定订单金额
        if amount and float(amount) > 0:
            actual_amount = Decimal(str(amount))
        else:
            actual_amount = product.price
        
        # 创建订单
        order = Order.objects.create(
            user=user,
            product=product,
            order_no=order_no,
            original_amount=product.price,
            actual_amount=actual_amount,
            status=0  # 待支付
        )
        
        logger.info(f"订单创建成功: {order_no}, 用户: {user.username}, 商品: {product.name}, 金额: {actual_amount}")
        return order
    
    @staticmethod
    def create_payment(order, payment_method):
        """
        创建支付记录
        :param order: 订单对象
        :param payment_method: 支付方式（1:支付宝, 2:微信支付, 3:银行卡）
        :return: 创建的支付记录
        """
        # 检查订单状态
        if order.status != 0:  # 0: 待支付
            raise ValueError("只有待支付订单可以创建支付记录")
        
        # 创建支付记录
        payment = Payment.objects.create(
            user=order.user,
            order=order,
            amount=order.actual_amount,
            payment_method=payment_method,
            status=0  # 待支付
        )
        
        logger.info(f"支付记录创建成功: 订单号: {order.order_no}, 支付方式: {payment_method}, 金额: {payment.amount}")
        return payment

class PaymentService:
    @staticmethod
    def create_payment(user, order, payment_method, description='', currency='CNY'):
        """
        创建支付记录
        """
        if order.status != 0:  # 0: 待支付
            raise ValueError("只有待支付订单可以创建支付")

        if order.user != user:
            raise ValueError("订单不属于当前用户")

        payment = Payment.objects.create(
            user=user,
            order=order,
            amount=order.actual_amount,
            currency=currency,
            payment_method=payment_method,
            description=description
        )
        return payment

    @classmethod
    def process_payment(cls, payment, **kwargs):
        """
        处理支付链接生成
        """
        try:
            payment_method = payment.payment_method
            payment_amount = float(payment.amount)
            logger.info(f"开始处理支付 ID: {payment.id}, 金额: {payment_amount}, 方式: {payment_method}")

            # 支付宝支付
            if payment_method == 1:
                # 使用支付宝客户端生成支付链接
                resp = cls.process_alipay_payment(payment)
                logger.info(f"支付宝支付链接生成 - 订单: {payment.order_no}, 链接: {resp.get('pay_url', '未生成')}")
                return resp

            # 微信支付
            elif payment_method == 2:
                pay_type = kwargs.get('pay_type', 'miniprog')  # 默认小程序支付
                
                if pay_type == 'pc':
                    # PC端支付
                    resp = cls.process_wechat_pc_payment(payment, **kwargs)
                    logger.info(f"微信PC支付参数生成 - 订单: {payment.order_no}")
                    return resp
                else:
                    # 小程序支付
                    resp = cls.process_wechat_miniprog_payment(payment, **kwargs)
                    logger.info(f"微信小程序支付参数生成 - 订单: {payment.order_no}")
                    return resp

            # 银行卡支付
            elif payment_method == 3:
                # 银行卡支付暂时没有在线支付，返回空的支付URL
                logger.info(f"银行卡支付 - 订单: {payment.order_no}, 无需生成支付链接")
                return {'success': True, 'pay_url': None, 'params': None}

            # 其他支付方式
            else:
                logger.error(f"不支持的支付方式: {payment_method}")
                return {'success': False, 'error': f"不支持的支付方式: {payment_method}"}

        except Exception as e:
            logger.error(f"支付处理失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': f"支付链接生成失败: {str(e)}"}

    @staticmethod
    def process_wechat_pc_payment(payment, **kwargs):
        """
        处理PC端微信支付（Native支付）
        
        :param payment: 支付对象
        :param kwargs: 支付额外参数
        :return: 支付结果
        """
        try:
            # 获取配置
            config = configparser.ConfigParser()
            config.read('config/config.ini')
            
            appid = config.get('wechat_pay', 'appid')
            mchid = config.get('wechat_pay', 'mchid')
            cert_serial_number = config.get('wechat_pay', 'cert_serial_number')
            apiv3_key = config.get('wechat_pay', 'api_key')
            
            # 加载密钥和证书
            private_key_path = config.get('wechat_pay', 'private_key_path')
            with open(private_key_path, 'r') as f:
                private_key = f.read()
                
            pub_key_path = config.get('wechat_pay', 'pub_key_path')
            with open(pub_key_path) as f:
                public_key = f.read()
                
            public_key_id = config.get('wechat_pay', 'PUBLIC_KEY_ID')
            
            # 初始化微信支付客户端
            wechat_pay = WeChatPay(
                wechatpay_type=WeChatPayType.NATIVE,
                mchid=mchid,
                private_key=private_key,
                cert_serial_no=cert_serial_number,
                appid=appid,
                apiv3_key=apiv3_key,
                cert_dir="./config/",
                public_key=public_key,
                public_key_id=public_key_id
            )
            
            # 生成订单号(如果没有)
            out_trade_no = payment.order.order_no
            
            # 商品描述
            description = payment.description or f"订单 {out_trade_no} 支付"
            
            # 金额(单位:分)
            amount = int(float(payment.amount) * 100)
            
            # 通知地址
            notify_url = settings.WECHAT_NOTIFY_URL
            
            # 调用统一下单接口
            result = wechat_pay.pay(
                description=description,
                out_trade_no=out_trade_no,
                notify_url=notify_url,
                amount={'total': amount}
            )
            
            # 处理返回结果
            if 'code' in result and result['code'] != 'SUCCESS':
                logger.error(f"微信PC支付下单失败: {result}")
                return {
                    'success': False,
                    'error': f"微信支付下单失败: {result.get('message', '未知错误')}"
                }
            
            # 解析JSON响应获取预支付ID
            json_str = result[1]
            result_dict = json.loads(json_str)
            
            # 获取支付参数(PC端是code_url)
            code_url = result_dict.get('code_url')
            
            if not code_url:
                logger.error(f"微信PC支付没有返回code_url: {result_dict}")
                return {
                    'success': False,
                    'error': '支付链接生成失败'
                }
            
            # 返回支付数据
            logger.info(f"微信PC支付下单成功 | 订单号: {out_trade_no} | 金额: {payment.amount}")
            return {
                'success': True,
                'pay_url': code_url,  # PC端是直接返回链接
                'params': {
                    'code_url': code_url
                },
                'out_trade_no': out_trade_no
            }
            
        except Exception as e:
            logger.error(f"处理微信PC支付异常: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"微信支付处理失败: {str(e)}"
            }

    @staticmethod
    def process_wechat_miniprog_payment(payment, **kwargs):
        """
        处理小程序微信支付
        
        :param payment: 支付对象
        :param kwargs: 支付额外参数（必须包含openid）
        :return: 支付结果
        """
        try:
            # 获取openid
            openid = kwargs.get('openid')
            if not openid:
                return {
                    'success': False,
                    'error': '微信小程序支付需要提供openid'
                }
            
            # 获取配置
            config = configparser.ConfigParser()
            config.read('config/config.ini')
            
            appid = config.get('wechat_pay', 'appid')
            mchid = config.get('wechat_pay', 'mchid')
            cert_serial_number = config.get('wechat_pay', 'cert_serial_number')
            apiv3_key = config.get('wechat_pay', 'api_key')
            
            # 加载密钥和证书
            private_key_path = config.get('wechat_pay', 'private_key_path')
            with open(private_key_path, 'r') as f:
                private_key = f.read()
                
            pub_key_path = config.get('wechat_pay', 'pub_key_path')
            with open(pub_key_path) as f:
                public_key = f.read()
                
            public_key_id = config.get('wechat_pay', 'PUBLIC_KEY_ID')
            
            # 初始化微信支付客户端
            wechat_pay = WeChatPay(
                wechatpay_type=WeChatPayType.MINIPROG,
                mchid=mchid,
                private_key=private_key,
                cert_serial_no=cert_serial_number,
                appid=appid,
                apiv3_key=apiv3_key,
                cert_dir="./config/",
                public_key=public_key,
                public_key_id=public_key_id
            )
            
            # 生成订单号(如果没有)
            out_trade_no = payment.order.order_no
            
            # 商品描述
            description = payment.description or f"订单 {out_trade_no} 支付"
            
            # 金额(单位:分)
            amount = int(float(payment.amount) * 100)
            
            # 通知地址
            notify_url = settings.WECHAT_NOTIFY_URL
            
            # 调用统一下单接口
            result = wechat_pay.pay(
                description=description,
                out_trade_no=out_trade_no,
                notify_url=notify_url,
                amount={'total': amount},
                payer={'openid': openid}
            )
            
            # 处理返回结果
            if 'code' in result and result['code'] != 'SUCCESS':
                logger.error(f"微信小程序支付下单失败: {result}")
                return {
                    'success': False,
                    'error': f"微信支付下单失败: {result.get('message', '未知错误')}"
                }
            
            # 解析JSON响应获取预支付ID
            json_str = result[1]
            result_dict = json.loads(json_str)
            prepay_id = result_dict.get('prepay_id')
            
            if not prepay_id:
                logger.error(f"微信小程序支付没有返回prepay_id: {result_dict}")
                return {
                    'success': False,
                    'error': '预支付ID获取失败'
                }
            
            # 生成小程序调起支付所需参数
            import secrets
            import string
            characters = string.ascii_letters + string.digits
            nonce_str = ''.join(secrets.choice(characters) for _ in range(32))
            
            pay_params = {
                'appId': appid,
                'timeStamp': str(int(time.time())),
                'nonceStr': nonce_str,
                'package': f'prepay_id={prepay_id}',
                'signType': 'RSA'
            }
            
            # 生成签名
            sign_params_list = [
                pay_params['appId'],
                pay_params['timeStamp'],
                pay_params['nonceStr'],
                pay_params['package']
            ]
            pay_params['paySign'] = wechat_pay.sign(sign_params_list)
            
            # 返回支付数据
            logger.info(f"微信小程序支付下单成功 | 订单号: {out_trade_no} | 金额: {payment.amount}")
            return {
                'success': True,
                'pay_url': None,  # 小程序支付没有支付链接
                'params': pay_params,  # 返回调起支付参数
                'out_trade_no': out_trade_no
            }
            
        except Exception as e:
            logger.error(f"处理微信小程序支付异常: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"微信支付处理失败: {str(e)}"
            }

    @staticmethod
    def get_payment_client(payment_method):
        """
        根据支付方式获取对应的支付客户端
        """
        if payment_method == 1:  # 支付宝
            return AlipayClient()
        elif payment_method == 2:  # 微信支付
            return WeChatPayClient()  # 使用新的客户端类
        elif payment_method == 3:  # 银行卡
            return BankPayClient()
        else:
            raise ValueError(f"不支持的支付方式: {payment_method}")
    
    @staticmethod
    def verify_payment_notification(data, payment_method):
        """
        验证支付通知的合法性
        """
        client = PaymentService.get_payment_client(payment_method)
        return client.verify_notification(data)

    @staticmethod
    def verify_wechat_notification(headers, body):
        """
        验证微信支付通知的签名
        :param headers: 请求头
        :param body: 请求体
        :return: 验证结果
        """
        try:
            # 读取微信支付配置
            wechat_config = settings.WECHAT_PAY_CONFIG
            mchid = wechat_config.get('mchid', '')
            
            # 获取必要的头信息
            wechat_pay_timestamp = headers.get('Wechatpay-Timestamp')
            wechat_pay_nonce = headers.get('Wechatpay-Nonce')
            wechat_pay_signature = headers.get('Wechatpay-Signature')
            wechat_pay_serial = headers.get('Wechatpay-Serial')
            
            if not all([wechat_pay_timestamp, wechat_pay_nonce, wechat_pay_signature, wechat_pay_serial]):
                return {'success': False, 'error': '缺少必要的微信支付请求头信息'}
            
            # 将请求体转换为字符串
            if isinstance(body, bytes):
                body_str = body.decode('utf-8')
            else:
                body_str = body
            
            # 构造验签名串
            message = f"{wechat_pay_timestamp}\n{wechat_pay_nonce}\n{body_str}\n"
            
            # TODO: 实现完整的微信支付签名验证
            # 此处简化实现，实际生产环境应当使用微信支付平台密钥进行验证
            # 由于验签需要微信支付平台证书和密钥，简化处理直接返回成功
            logger.warning("微信支付通知签名验证被简化处理，生产环境应实现完整验证")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"微信支付通知验签失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': f"验签失败: {str(e)}"}

    @staticmethod
    def decrypt_wechat_notification(headers, body):
        """
        解密微信支付通知数据
        :param headers: 请求头
        :param body: 请求体
        :return: 解密后的数据
        """
        try:
            # 读取微信支付配置
            wechat_config = settings.WECHAT_PAY_CONFIG
            api_key = wechat_config.get('api_key', '')
            api_key_v3 = wechat_config.get('api_key_v3', '')
            mchid = wechat_config.get('mchid', '')
            
            # 获取必要的头信息
            wechat_pay_timestamp = headers.get('Wechatpay-Timestamp')
            wechat_pay_nonce = headers.get('Wechatpay-Nonce')
            wechat_pay_signature = headers.get('Wechatpay-Signature')
            wechat_pay_serial = headers.get('Wechatpay-Serial')
            
            if not all([wechat_pay_timestamp, wechat_pay_nonce, wechat_pay_signature, wechat_pay_serial]):
                return {'success': False, 'error': '缺少必要的微信支付请求头信息'}
            
            # 解析通知数据
            if isinstance(body, bytes):
                body_str = body.decode('utf-8')
            else:
                body_str = body
            
            notification_data = json.loads(body_str)
            logger.info(f"微信支付通知原始数据: {notification_data}")
            
            # 获取加密数据
            resource = notification_data.get('resource', {})
            ciphertext = resource.get('ciphertext')
            nonce = resource.get('nonce')
            associated_data = resource.get('associated_data')
            
            if not all([ciphertext, nonce]):
                return {'success': False, 'error': '缺少必要的加密数据'}
            
            # 使用API V3密钥解密
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            import base64
            
            api_key_bytes = api_key_v3.encode('utf-8')
            nonce_bytes = nonce.encode('utf-8')
            associated_data_bytes = associated_data.encode('utf-8') if associated_data else b''
            ciphertext_bytes = base64.b64decode(ciphertext)
            
            aesgcm = AESGCM(api_key_bytes)
            try:
                plaintext_bytes = aesgcm.decrypt(nonce_bytes, ciphertext_bytes, associated_data_bytes)
                plaintext = plaintext_bytes.decode('utf-8')
                decrypted_data = json.loads(plaintext)
                logger.info(f"微信支付通知解密成功: {decrypted_data}")
                return {'success': True, 'data': decrypted_data}
            except Exception as e:
                logger.error(f"微信支付通知解密失败: {str(e)}", exc_info=True)
                return {'success': False, 'error': f"解密失败: {str(e)}"}
            
        except Exception as e:
            logger.error(f"微信支付通知解析失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': f"解析通知失败: {str(e)}"}

    @staticmethod
    def _handle_vip_payment(order, user, product, payment):
        """
        处理VIP会员支付专用逻辑
        """
        # 计算VIP时长（根据产品配置决定，示例为30天）
        duration = timedelta(days=product.valid_days if hasattr(product, 'valid_days') else 30)

        with transaction.atomic():
            # 获取或创建VIP记录
            vip, created = UserVIP.objects.get_or_create(
                user=user,
                defaults={
                    'end_time': timezone.now() + duration,
                    'last_payment': payment
                }
            )

            if not created:
                # 续费逻辑
                now = timezone.now()
                if vip.end_time > now:  # 未过期，叠加时间
                    vip.end_time += duration
                else:  # 已过期，重新计算
                    vip.end_time = now + duration

                vip.is_active = True
                vip.last_payment = payment
                vip.save()

            # 更新用户角色和积分
            user.userRole = "user_vip"
            # 普通积分和VIP积分分开处理
            user.points += product.points  # 普通积分
            user.vip_points += product.gift_points  # VIP专属积分
            user.save()

            logger.info(
                f"VIP订单处理成功 | 订单:{order.order_no} | "
                f"用户:{user.username} | "
                f"有效期至:{vip.end_time} | "
                f"新增普通积分:{product.points} | "
                f"新增VIP积分:{product.gift_points}"
            )

    @classmethod
    def update_payment_status(cls, payment, trade_no, payment_status, payment_amount):
        """
        统一更新支付状态的方法
        :param payment: 支付对象
        :param trade_no: 交易号（支付平台）
        :param payment_status: 支付状态 (success/fail)
        :param payment_amount: 支付金额
        :return: 处理结果
        """
        try:
            with transaction.atomic():
                # 检查支付状态
                if payment.status != 0:  # 0: 待支付
                    logger.warning(f"支付状态已更新，不能重复处理: {payment.id}, 当前状态: {payment.status}")
                    return {'success': False, 'error': '支付状态已更新，不能重复处理'}
                
                # 检查金额
                if payment_amount and Decimal(str(payment_amount)) != payment.amount:
                    logger.warning(f"支付金额不匹配: 期望 {payment.amount}, 实际 {payment_amount}")
                    return {'success': False, 'error': '支付金额不匹配'}
                
                # 更新支付状态
                if payment_status == 'success':
                    payment.status = 1  # 支付成功
                    payment.trade_no = trade_no
                    payment.payment_time = timezone.now()
                    payment.save()
                    
                    # 更新订单状态
                    order = payment.order
                    order.status = 1  # 已支付
                    order.payment_time = timezone.now()
                    order.save()
                    
                    # 处理业务逻辑
                    cls._process_payment_success(payment)
                    
                    logger.info(f"支付成功处理完成: 订单 {order.order_no}, 交易号 {trade_no}")
                    return {'success': True, 'message': '支付成功'}
                else:
                    payment.status = 2  # 支付失败
                    payment.save()
                    logger.info(f"支付失败: 订单 {payment.order.order_no}")
                    return {'success': True, 'message': '支付失败'}
                
        except Exception as e:
            logger.error(f"更新支付状态失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': f"更新支付状态失败: {str(e)}"}
    
    @classmethod
    def _process_payment_success(cls, payment):
        """
        处理支付成功后的业务逻辑
        :param payment: 支付对象
        """
        try:
            # 获取订单和用户
            order = payment.order
            user = payment.user
            
            # 根据不同产品类型处理业务逻辑
            product = order.product
            if product and hasattr(product, 'description'):
                # VIP会员处理
                if "月卡" in product.description:
                    days = 30
                    if "季卡" in product.description:
                        days = 90
                    elif "年卡" in product.description:
                        days = 365
                    
                    # 更新会员状态
                    user.role = '1'  # 设置为VIP
                    if user.vip_expire_time and user.vip_expire_time > timezone.now():
                        # 已有VIP，延长时间
                        user.vip_expire_time = user.vip_expire_time + timedelta(days=days)
                    else:
                        # 新开通VIP
                        user.vip_expire_time = timezone.now() + timedelta(days=days)
                    user.save()
                    logger.info(f"用户 {user.username} VIP开通成功, 到期时间: {user.vip_expire_time}")
                
                # 积分充值处理
                elif "积分" in product.description:
                    points = product.points
                    if points > 0:
                        # 增加用户积分
                        user.points = user.points + points
                        user.save()
                        logger.info(f"用户 {user.username} 积分充值成功, 增加 {points} 点")
                
                # 其他产品处理逻辑...
                
            logger.info(f"支付成功业务处理完成: 用户 {user.username}, 订单 {order.order_no}")
            
        except Exception as e:
            logger.error(f"支付成功业务处理失败: {str(e)}", exc_info=True)
            # 不影响支付流程，记录错误但不抛出

    @staticmethod
    @transaction.atomic
    def create_refund(payment, amount, reason=''):
        """
        创建退款申请
        """
        if payment.status != 1:  # 已支付
            raise ValueError("只有已支付的订单才能退款")
        
        if float(amount) > float(payment.amount):
            raise ValueError("退款金额不能大于支付金额")
        
        refund = Refund.objects.create(
            payment=payment,
            amount=amount,
            reason=reason
        )
        return refund
    
    @staticmethod
    @transaction.atomic
    def process_refund(refund):
        """
        处理退款，调用第三方支付平台
        """
        if refund.status != 0:  # 处理中
            raise ValueError("只有处理中状态的退款记录可以处理")
        
        # 获取支付客户端
        client = PaymentService.get_payment_client(refund.payment.payment_method)
        refund_data = client.create_refund(refund)
        
        if not refund_data.get('success'):
            raise ValueError(refund_data.get('error', '退款创建失败'))
        
        return refund_data
    
    @staticmethod
    @transaction.atomic
    def update_refund_status(refund, status, transaction_id=None, raw_response=None):
        """
        更新退款状态并处理相关业务
        """
        if refund.status == status:
            return refund
        
        refund.status = status
        if transaction_id:
            refund.transaction_id = transaction_id
        if raw_response:
            refund.raw_response = raw_response
        if status == 1:  # 成功
            refund.refund_time = timezone.now()
        refund.save()
        
        # 退款成功后的业务处理
        if status == 1:
            # 更新支付状态
            payment = refund.payment
            payment.status = 3  # 已退款
            payment.save()
            
            # 更新订单状态
            order = payment.order
            order.status = 5  # 已退款
            order.save()
            
            logger.info(f"订单{order.order_no}退款成功，退款金额{refund.amount}")
        
        return refund 

    