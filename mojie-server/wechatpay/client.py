from django.conf import settings
from wechatpy import WeChatPay
from wechatpy.exceptions import WeChatPayException  # 新版本可能使用这个
from wechatpy.utils import random_string
from wechatpy.pay.api import WeChatOrder, WeChatRefund
import logging
from typing import Dict, Optional, Union, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class WeChatPayClient:
    """
    微信支付客户端封装类，基于wechatpy SDK实现

    支持功能：
    - 统一下单（JSAPI/NATIVE/APP/H5）
    - 支付通知验证
    - 退款申请
    - 退款查询
    - 订单查询
    """

    def __init__(self):
        """
        初始化微信支付客户端

        配置从Django settings中读取:
        - WECHAT_APP_ID: 微信应用ID
        - WECHAT_MCH_ID: 微信商户号
        - WECHAT_API_KEY: 微信支付API密钥
        - WECHAT_NOTIFY_URL: 支付通知回调地址
        - WECHAT_CERT_PATH: 微信支付证书路径
        - WECHAT_KEY_PATH: 微信支付密钥路径
        """
        self.app_id = settings.WECHAT_APP_ID
        self.mch_id = settings.WECHAT_MCH_ID
        self.api_key = settings.WECHAT_API_KEY
        self.notify_url = settings.WECHAT_NOTIFY_URL
        self.cert_path = settings.WECHAT_CERT_PATH
        self.key_path = settings.WECHAT_KEY_PATH

        # 初始化微信支付客户端
        self.client = WeChatPay(
            appid=self.app_id,
            api_key=self.api_key,
            mch_id=self.mch_id,
            sub_appid=None,
            sub_mch_id=None,
            mch_cert=self.cert_path,
            mch_key=self.key_path
        )

        # 初始化订单和退款API
        self.order_api = WeChatOrder(self.client)
        self.refund_api = WeChatRefund(self.client)

    def create_payment(
            self,
            payment: object,
            trade_type: str = 'NATIVE',
            client_ip: str = None,
            openid: str = None,
            **kwargs
    ) -> Dict[str, Union[bool, str, Dict]]:
        """
        创建微信支付订单

        :param payment: 支付对象，需包含以下属性:
            - description: 商品描述
            - amount: 支付金额(元)
            - order.order_no: 商户订单号
        :param trade_type: 交易类型(JSAPI/NATIVE/APP/H5)
        :param client_ip: 客户端IP地址
        :param openid: 用户openid(JSAPI支付需要)
        :param kwargs: 其他支付参数
        :return: 支付结果字典
        """
        try:
            # 生成随机字符串
            nonce_str = random_string(32)

            # 构建支付参数
            params = {
                'body': payment.description[:128],
                'out_trade_no': payment.order.order_no,
                'total_fee': int(float(payment.amount) * 100),  # 转换为分
                'notify_url': self.notify_url,
                'trade_type': trade_type,
                'spbill_create_ip': client_ip or '127.0.0.1',
                'nonce_str': nonce_str,
                **kwargs
            }

            # JSAPI支付需要openid
            if trade_type == 'JSAPI' and openid:
                params['openid'] = openid

            # 调用统一下单接口
            result = self.order_api.create(**params)

            # 根据交易类型返回不同格式的支付参数
            if trade_type == 'NATIVE':
                return {
                    'success': True,
                    'payment_url': result.get('code_url'),
                    'params': result
                }
            elif trade_type == 'JSAPI':
                return {
                    'success': True,
                    'params': self._get_jsapi_params(result.get('prepay_id'))
                }
            elif trade_type == 'APP':
                return {
                    'success': True,
                    'params': self._get_app_params(result.get('prepay_id'))
                }
            else:
                return {
                    'success': True,
                    'params': result
                }

        except WeChatPayException  as e:
            logger.error(f"微信支付创建失败: {e.message}", exc_info=True)
            return {
                'success': False,
                'error': e.message,
                'code': e.err_code
            }
        except Exception as e:
            logger.error(f"微信支付创建异常: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def verify_notification(self, data: Dict) -> bool:
        """
        验证微信支付通知的合法性

        :param data: 支付通知数据
        :return: 验证结果
        """
        try:
            return self.client.check_signature(data)
        except Exception as e:
            logger.error(f"微信支付通知验证失败: {str(e)}", exc_info=True)
            return False

    def create_refund(self, refund: object) -> Dict[str, Union[bool, str, Dict]]:
        """
        创建微信支付退款

        :param refund: 退款对象，需包含以下属性:
            - id: 退款ID
            - amount: 退款金额(元)
            - reason: 退款原因
            - payment.order.order_no: 原支付订单号
            - payment.amount: 原支付金额(元)
        :return: 退款结果字典
        """
        try:
            # 生成随机字符串
            nonce_str = random_string(32)

            # 构建退款参数
            params = {
                'out_trade_no': refund.payment.order.order_no,
                'out_refund_no': f"refund_{refund.id}",
                'total_fee': int(float(refund.payment.amount) * 100),
                'refund_fee': int(float(refund.amount) * 100),
                'refund_desc': refund.reason[:80] if refund.reason else '',
                'nonce_str': nonce_str
            }

            # 调用退款接口
            result = self.refund_api.apply(**params)

            return {
                'success': True,
                'transaction_id': result.get('refund_id'),
                'raw_response': result
            }

        except WeChatPayException  as e:
            logger.error(f"微信支付退款创建失败: {e.message}", exc_info=True)
            return {
                'success': False,
                'error': e.message,
                'code': e.err_code
            }
        except Exception as e:
            logger.error(f"微信支付退款创建异常: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def query_refund(self, refund: object) -> Dict[str, Union[bool, str, Dict]]:
        """
        查询微信支付退款状态

        :param refund: 退款对象，需包含id属性
        :return: 查询结果字典
        """
        try:
            # 生成随机字符串
            nonce_str = random_string(32)

            # 构建查询参数
            params = {
                'out_refund_no': f"refund_{refund.id}",
                'nonce_str': nonce_str
            }

            # 调用退款查询接口
            result = self.refund_api.query(**params)

            # 解析退款状态
            refund_status = None
            if 'refund_status_0' in result:
                refund_status = result['refund_status_0']
            elif 'status' in result:
                refund_status = result['status']

            return {
                'success': True,
                'status': refund_status,
                'raw_response': result
            }

        except WeChatPayException  as e:
            logger.error(f"微信支付退款查询失败: {e.message}", exc_info=True)
            return {
                'success': False,
                'error': e.message,
                'code': e.err_code
            }
        except Exception as e:
            logger.error(f"微信支付退款查询异常: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def query_order(self, out_trade_no: str) -> Dict[str, Union[bool, str, Dict]]:
        """
        查询微信支付订单状态

        :param out_trade_no: 商户订单号
        :return: 查询结果字典
        """
        try:
            # 生成随机字符串
            nonce_str = random_string(32)

            # 构建查询参数
            params = {
                'out_trade_no': out_trade_no,
                'nonce_str': nonce_str
            }

            # 调用订单查询接口
            result = self.order_api.query(**params)

            return {
                'success': True,
                'status': result.get('trade_state'),
                'raw_response': result
            }

        except WeChatPayException  as e:
            logger.error(f"微信支付订单查询失败: {e.message}", exc_info=True)
            return {
                'success': False,
                'error': e.message,
                'code': e.err_code
            }
        except Exception as e:
            logger.error(f"微信支付订单查询异常: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def _get_jsapi_params(self, prepay_id: str) -> Dict[str, str]:
        """
        生成JSAPI支付所需的参数

        :param prepay_id: 预支付ID
        :return: JSAPI支付参数
        """
        params = {
            'appId': self.app_id,
            'timeStamp': str(int(datetime.now().timestamp())),
            'nonceStr': random_string(32),
            'package': f"prepay_id={prepay_id}",
            'signType': 'MD5'
        }
        params['paySign'] = self.client.sign(params)
        return params

    def _get_app_params(self, prepay_id: str) -> Dict[str, str]:
        """
        生成APP支付所需的参数

        :param prepay_id: 预支付ID
        :return: APP支付参数
        """
        params = {
            'appid': self.app_id,
            'partnerid': self.mch_id,
            'prepayid': prepay_id,
            'package': 'Sign=WXPay',
            'noncestr': random_string(32),
            'timestamp': str(int(datetime.now().timestamp()))
        }
        params['sign'] = self.client.sign(params)
        return params