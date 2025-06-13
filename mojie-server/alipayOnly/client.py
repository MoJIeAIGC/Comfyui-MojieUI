from django.conf import settings
from alipay import AliPay
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

class AlipayClient:
    def __init__(self, app_id=None, notify_url=None, return_url=None, private_key_path=None, 
                 public_key_path=None, sign_type=None, debug=None, gateway_url=None, 
                 aes_key=None, encrypt_key=False):
        """
        初始化支付宝客户端
        :param app_id: 支付宝应用ID
        :param notify_url: 异步通知地址
        :param return_url: 同步通知地址
        :param private_key_path: 应用私钥路径
        :param public_key_path: 支付宝公钥路径
        :param sign_type: 签名方式
        :param debug: 是否使用沙箱环境
        :param gateway_url: 支付宝网关地址
        :param aes_key: AES密钥
        :param encrypt_key: 是否启用AES加密
        """
        # 从settings获取默认配置
        config = settings.ALIPAY_CONFIG
        
        # 使用传入的参数覆盖默认配置
        self.app_id = app_id or config.get('appid')
        self.notify_url = notify_url or config.get('app_notify_url')
        self.return_url = return_url or config.get('return_url')
        self.private_key_path = private_key_path or config.get('app_private_key_path')
        self.public_key_path = public_key_path or config.get('alipay_public_key_path')
        self.sign_type = sign_type or config.get('sign_type', 'RSA2')
        self.debug = debug if debug is not None else config.get('debug', True)
        self.gateway_url = gateway_url or config.get('gateway_url')
        self.aes_key = aes_key or config.get('aes_key')
        self.encrypt_key = encrypt_key if encrypt_key is not None else config.get('encrypt_key', False)
        
        # 初始化支付宝客户端
        self._init_alipay()
        
    def _init_alipay(self):
        """初始化支付宝客户端"""
        try:
            # 读取密钥文件
            with open(self.private_key_path, 'r') as f:
                app_private_key_string = f.read()
            with open(self.public_key_path, 'r') as f:
                alipay_public_key_string = f.read()
            
            # 创建支付宝客户端
            self.alipay = AliPay(
                appid=self.app_id,
                app_notify_url=self.notify_url,
                app_private_key_string=app_private_key_string,
                alipay_public_key_string=alipay_public_key_string,
                sign_type=self.sign_type,
                debug=self.debug
            )
            
            # 设置网关地址
            if self.gateway_url:
                self.alipay._gateway = self.gateway_url
            
            logger.info(f"支付宝客户端初始化成功: app_id={self.app_id}, debug={self.debug}")
            
        except Exception as e:
            logger.error(f"支付宝客户端初始化失败: {str(e)}")
            raise
    
    def create_payment(self, payment):
        """
        创建支付订单
        :param payment: Payment对象
        :return: dict
        """
        try:
            # 构建支付参数
            order_string = self.alipay.api_alipay_trade_page_pay(
                out_trade_no=payment.order.order_no,
                total_amount=str(payment.amount),
                subject=payment.description or "商品购买",
                return_url=self.return_url,
                notify_url=self.notify_url
            )
            
            # 生成支付链接
            pay_url = f"{self.gateway_url}?{order_string}"
            
            logger.info(f"创建支付订单成功: order_no={payment.order.order_no}, amount={payment.amount}")
            logger.info(f"生成链接成功: pay_url={pay_url}")
            return {
                'success': True,
                'pay_url': pay_url,
                'order_string': order_string
            }
            
        except Exception as e:
            logger.error(f"创建支付订单失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_notification(self, data):
        """
        验证支付宝通知
        :param data: 通知数据
        :return: dict
        """
        try:
            # 验证签名
            signature = data.pop("sign")
            success = self.alipay.verify(data, signature)
            
            if success:
                logger.info("支付宝通知验证成功")
                return {
                    'success': True,
                    'data': data
                }
            else:
                logger.warning("支付宝通知验证失败")
                return {
                    'success': False,
                    'error': '签名验证失败'
                }
                
        except Exception as e:
            logger.error(f"验证支付宝通知失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_refund(self, refund):
        """
        创建退款
        :param refund: Refund对象
        :return: dict
        """
        try:
            # 调用退款接口
            result = self.alipay.api_alipay_trade_refund(
                out_trade_no=refund.payment.order.order_no,
                refund_amount=str(refund.amount),
                refund_reason=refund.reason
            )
            
            if result.get('code') == '10000':
                logger.info(f"退款申请成功: order_no={refund.payment.order.order_no}, amount={refund.amount}")
                return {
                    'success': True,
                    'data': result
                }
            else:
                logger.warning(f"退款申请失败: {result.get('sub_msg')}")
                return {
                    'success': False,
                    'error': result.get('sub_msg')
                }
                
        except Exception as e:
            logger.error(f"创建退款失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def query_order(self, order_no):
        """
        查询订单状态
        :param order_no: 订单号
        :return: dict
        """
        try:
            result = self.alipay.api_alipay_trade_query(out_trade_no=order_no)
            
            if result.get('code') == '10000':
                logger.info(f"查询订单成功: order_no={order_no}")
                return {
                    'success': True,
                    'data': result
                }
            else:
                logger.warning(f"查询订单失败: {result.get('sub_msg')}")
                return {
                    'success': False,
                    'error': result.get('sub_msg')
                }
                
        except Exception as e:
            logger.error(f"查询订单失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def query_refund(self, refund):
        """
        查询支付宝退款状态
        """
        try:
            # 调用退款查询接口
            result = self.alipay.api_alipay_trade_fastpay_refund_query(
                out_trade_no=refund.payment.order.order_no,
                out_request_no=f"refund_{refund.id}"
            )
            
            # 记录日志
            logger.info(f"查询支付宝退款状态: {refund.id}, 环境: {'沙箱' if self.debug else '生产'}")
            
            if result.get('code') == '10000':
                return {
                    'success': True,
                    'status': result.get('refund_status'),
                    'raw_response': result
                }
            else:
                return {
                    'success': False,
                    'error': result.get('msg', '查询失败')
                }
        except Exception as e:
            logger.error(f"查询支付宝退款状态失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            } 