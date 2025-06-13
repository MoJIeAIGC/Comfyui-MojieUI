from dateutil.relativedelta import relativedelta
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils.http import urlencode
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiExample, extend_schema, OpenApiResponse, OpenApiParameter
from wechatpy import WeChatOAuth
from decimal import Decimal

import order
from bankpay.client import BankPayClient
from common.response_utils import ResponseUtil
from djangoProject import settings
from django.shortcuts import redirect
from urllib.parse import urlencode
import json
import logging
import time
from django.forms.models import model_to_dict
from urllib.parse import quote
from Crypto.Cipher import AES
import base64
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from alipay import AliPay
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
import configparser
from django.http import JsonResponse
from rest_framework.views import APIView
from wechatpayv3 import WeChatPay, WeChatPayType
from wechatpay.client import WeChatPayClient
from .models import Order, Payment, Refund, Product,UserVIP
from .serializers import (
    PaymentSerializer, 
    PaymentCreateSerializer,
    RefundSerializer,
    RefundCreateSerializer,
    PaymentNotificationSerializer,
    OrderSerializer,
    ProductSerializer
)
from .services import PaymentService, OrderService
from user.permissions import IsOwnerOrReadOnly
import uuid
from django.contrib.auth import get_user_model
from common.response_utils import ResponseUtil
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
logger = logging.getLogger(__name__)
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import AllowAny,IsAuthenticated
import random
from rest_framework import permissions
from django.core.paginator import Paginator
from user.models import SysUser
from dateutil.relativedelta import relativedelta

class AliPayView(APIView):
    """
    支付宝支付视图
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        生成支付链接
        """
        try:
            # 获取商品和数量
            product_id = request.data.get('product_id')
            if not product_id:
                return ResponseUtil.error("缺少商品ID")

            # 创建订单
            product = Product.objects.filter(id=product_id).first()
            if not product:
                return ResponseUtil.error("商品不存在")

            # 创建订单和支付记录
            order_service = OrderService()
            order = order_service.create_order(
                user=request.user,
                product=product,
                amount=request.data.get('custom_amount')
            )

            # 创建支付记录
            payment = order_service.create_payment(
                order=order,
                payment_method=1  # 1: 支付宝
            )

            # 生成支付宝支付链接
            payment_service = PaymentService()
            payment_data = payment_service.process_alipay_payment(payment)
            
            if not payment_data.get('success'):
                return ResponseUtil.error(payment_data.get('error', '支付创建失败'))

            return ResponseUtil.success({
                'order_id': order.id,
                'order_no': order.order_no,
                'amount': str(order.actual_amount),
                'payment_method': 1,
                'payment_url': payment_data.get('pay_url'),
                'status': 'pending'
            }, message="支付创建成功")

        except Exception as e:
            logger.error(f"支付宝支付创建失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(f"支付创建失败: {str(e)}")


class AlipayNotifyView(APIView):
    permission_classes = [AllowAny]  # 支付宝回调不需要认证

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description="成功处理通知"),
            400: OpenApiResponse(description="通知验证失败"),
            500: OpenApiResponse(description="服务器错误")
        },
        methods=["POST"],
        exclude=True  # 通常支付通知接口不需要在API文档中展示
    )
    def post(self, request):
        try:
            # 1. 获取并验证基础参数
            data = request.POST.dict()
            signature = data.pop('sign', None)
            
            if not signature:
                logger.error("支付宝异步通知缺少签名参数")
                return Response("fail - missing signature", status=status.HTTP_400_BAD_REQUEST)

            # 2. 初始化支付宝
            alipay = AliPay(
                appid=settings.ALIPAY_CONFIG['appid'],
                app_notify_url=settings.ALIPAY_CONFIG['app_notify_url'],
                app_private_key_string=open(settings.ALIPAY_CONFIG['app_private_key_path']).read(),
                alipay_public_key_string=open(settings.ALIPAY_CONFIG['alipay_public_key_path']).read(),
                sign_type=settings.ALIPAY_CONFIG['sign_type'],
                debug=settings.ALIPAY_CONFIG['debug']
            )

            # 3. 验证签名和交易状态
            if not alipay.verify(data, signature):
                logger.error(f"签名验证失败 | 原始数据: {data} | 签名: {signature}")
                return Response("fail - invalid signature", status=status.HTTP_400_BAD_REQUEST)

            trade_status = data.get('trade_status')
            if trade_status not in ('TRADE_SUCCESS', 'TRADE_FINISHED'):
                logger.warning(f"未处理的交易状态: {trade_status} | 订单: {data.get('out_trade_no')}")
                return Response("fail - invalid trade status", status=status.HTTP_400_BAD_REQUEST)

            # 4. 处理业务逻辑
            out_trade_no = data.get('out_trade_no')
            trade_no = data.get('trade_no')  # 支付宝交易号
            total_amount = float(data.get('total_amount', 0))
            
            logger.info(f"支付成功通知 | 订单: {out_trade_no} | 金额: {total_amount} | 支付宝交易号: {trade_no}")
            
            try:
                with transaction.atomic():
                    # 查询订单和支付信息
                    order = Order.objects.get(order_no=out_trade_no)
                    payment = Payment.objects.get(order=order)

                    # 验证订单金额是否匹配
                    if abs(float(order.actual_amount) - total_amount) > 0.01:  # 允许0.01元的误差
                        logger.error(f"订单金额不匹配 | 订单金额: {order.actual_amount} | 支付金额: {total_amount}")
                        return Response("fail - amount mismatch", status=status.HTTP_400_BAD_REQUEST)

                    # 调用支付服务处理状态更新及后续业务逻辑
                    PaymentService.update_payment_status(
                        payment=payment,
                        status=1,  # 已支付
                        transaction_id=trade_no,
                        raw_response=data
                    )

                    logger.info(f"订单支付状态更新成功 | 订单: {out_trade_no}")
            except Order.DoesNotExist:
                logger.error(f"订单不存在 | 订单: {out_trade_no}")
                return Response("fail - order not found", status=status.HTTP_404_NOT_FOUND)
            except Payment.DoesNotExist:
                logger.error(f"支付记录不存在 | 订单: {out_trade_no}")
                return Response("fail - payment not found", status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger.error(f"处理订单异常 | 订单: {out_trade_no} | 异常: {str(e)}", exc_info=True)
                return Response(f"fail - {str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 5. 必须返回success（支付宝文档要求）
            return Response("success")

        except Exception as e:
            logger.error(f"处理异步通知异常: {str(e)}", exc_info=True)
            return Response(f"error - {str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AlipayReturnView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            # 1. 验证支付宝回调（保持原有验证逻辑）
            data = request.GET.dict()
            signature = data.pop('sign', None)

            if not signature:
                logger.error("缺少签名参数")
                return redirect(f"https://www.qihuaimage.com/payStatus?status=fail&reason=missing_signature")

            alipay = AliPay(
                appid=settings.ALIPAY_CONFIG['appid'],
                app_notify_url=settings.ALIPAY_CONFIG['app_notify_url'],
                app_private_key_string=open(settings.ALIPAY_CONFIG['app_private_key_path']).read(),
                alipay_public_key_string=open(settings.ALIPAY_CONFIG['alipay_public_key_path']).read(),
                sign_type=settings.ALIPAY_CONFIG['sign_type'],
                debug=settings.ALIPAY_CONFIG['debug']
            )

            if not alipay.verify(data, signature):
                logger.error(f"签名验证失败: {data}")
                return redirect(f"https://www.qihuaimage.com/payStatus?status=fail&reason=invalid_signature")

            # 2. 处理订单业务
            out_trade_no = data.get('out_trade_no')
            try:
                order = Order.objects.get(order_no=out_trade_no)
                payment = Payment.objects.get(order=order)

                # 根据debug模式决定处理逻辑
                if settings.ALIPAY_CONFIG['debug']:
                    # 测试环境：在同步回调中处理订单状态（模拟异步通知的处理逻辑）
                    if payment.status == 0 and order.status == 0:  # 只有未支付的订单才处理
                        # 处理用户积分和VIP
                        user = order.user
                        # 获取用户信息
                        if user:
                            # 获取订单关联产品的 points
                            product_points = order.product.points

                            # 检查商品的 method 字段是否为 vip1
                            if order.product.method == 'vip1':
                                start_time = timezone.now()
                                if UserVIP.objects.filter(user=user, is_active=1).exists():
                                    user_vip = UserVIP.objects.get(user=user)
                                    user_vip.end_time = user_vip.end_time + relativedelta(months=1)
                                    user_vip.save()
                                else:
                                    end_time = start_time + relativedelta(months=1)
                                    UserVIP.objects.create(
                                        user=user,
                                        start_time=start_time,
                                        end_time=end_time,
                                        level='vip_basic',
                                    )
                                user.vip_points += product_points
                                user.save()
                            elif order.product.method == 'vip2':
                                start_time = timezone.now()
                                if UserVIP.objects.filter(user=user, is_active=1).exists():
                                    user_vip = UserVIP.objects.get(user=user)
                                    user_vip.end_time = user_vip.end_time + relativedelta(months=6)
                                    user_vip.save()
                                else:
                                    end_time = start_time + relativedelta(months=6)
                                    UserVIP.objects.create(
                                        user=user,
                                        start_time=start_time,
                                        end_time=end_time,
                                        level='vip_basic',
                                    )
                                user.vip_points += product_points
                                user.save()
                            elif order.product.method == 'vip3':
                                start_time = timezone.now()
                                if UserVIP.objects.filter(user=user, is_active=1).exists():
                                    user_vip = UserVIP.objects.get(user=user)
                                    user_vip.end_time = user_vip.end_time + relativedelta(months=12)
                                    user_vip.save()
                                else:
                                    end_time = start_time + relativedelta(months=12)
                                    UserVIP.objects.create(
                                        user=user,
                                        start_time=start_time,
                                        end_time=end_time,
                                        level='vip_basic',
                                    )
                                user.vip_points += product_points
                                user.save()
                            else:
                                user.points += product_points
                                user.save()
                        else:
                            return ResponseUtil.error(message='用户不存在')

                        # 更新订单和支付状态
                        current_time = timezone.now()
                        order.status = 1  # 已支付
                        order.save()
                        payment.status = 1  # 已支付
                        payment.transaction_id = data.get('trade_no', '')
                        payment.raw_response = data
                        payment.pay_time = current_time  # 设置支付时间
                        payment.save()

                        logger.info(f"测试环境：同步回调处理订单成功 | 订单: {out_trade_no}")
                else:
                    # 生产环境：只检查支付状态，不修改订单信息
                    if payment.status == 1 and order.status == 1:
                        logger.info(f"生产环境同步通知：订单已处理 | 订单: {out_trade_no}")
                    else:
                        logger.info(f"生产环境同步通知：订单待处理 | 订单: {out_trade_no}")
                        # 注意：这里不更新订单状态，由异步通知处理

                # 3. 构建跳转URL参数
                redirect_params = {
                    'status': 'success',
                    'order_no': order.order_no,
                    'amount': str(order.actual_amount),
                    'payment_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'product_name': order.product.description if order.product else '',
                    'trade_no': data.get('trade_no', '')  # 从同步通知获取交易号
                }

                # 4. 跳转到前端页面（URL编码参数）http://192.168.0.103:8100/home
                # https://www.qihuaimage.com/home
                frontend_url = "https://www.qihuaimage.com/payStatus?" + urlencode(redirect_params)
                return redirect(frontend_url)

            except (Order.DoesNotExist, Payment.DoesNotExist) as e:
                logger.error(f"订单不存在: {out_trade_no}")
                return redirect(f"https://www.qihuaimage.com/payStatus?status=error&reason=order_not_found")

        except Exception as e:
            logger.error(f"处理异常: {str(e)}", exc_info=True)
            return redirect(f"https://www.qihuaimage.com/payStatus?status=error&reason=server_error")


class OrderView(APIView):
    """订单相关接口"""

    @extend_schema(
        parameters=[]
    )
    def get(self, request):
        """获取订单列表"""
        orders = Order.objects.filter(user=request.user, is_delete=False)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    @extend_schema(
        parameters=[],
        responses={
            201: None,
            400: {
                "description": "参数错误",
                "examples": {
                    "application/json": {
                        "field": ["错误信息"]
                    }
                }
            }
        }
    )
    def post(self, request):
        """创建订单"""
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderDetailView(APIView):
    """订单详情接口"""

    @extend_schema(
        parameters=[]
    )
    def get(self, request, pk):
        """获取订单详情"""
        order = get_object_or_404(Order, pk=pk, user=request.user, is_delete=False)
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    @extend_schema(
        parameters=[],
        responses={
            200: {
                "description": "支付订单创建成功",
                "examples": {
                    "application/json": {
                        "success": True,
                        "payment_url": "https://example.com/pay/123",
                        "payment_id": 1
                    }
                }
            },
            400: {
                "description": "支付创建失败",
                "examples": {
                    "application/json": {
                        "success": False,
                        "error": "支付创建失败原因"
                    }
                }
            }
        }
    )
    def post(self, request, pk):
        """创建支付订单"""
        order = get_object_or_404(Order, pk=pk, user=request.user, is_delete=False)
        try:
            # 创建支付记录
            payment = PaymentService.create_payment(
                user=request.user,
                order=order,
                payment_method=1,  # 支付宝支付
                description=f"订单支付 - {order.order_no}"
            )
            
            # 处理支付
            payment_data = PaymentService.process_payment(payment)
            
            if not payment_data.get('success'):
                return Response({
                    'success': False,
                    'error': payment_data.get('error', '支付创建失败')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': True,
                'payment_url': payment_data.get('payment_url'),
                'payment_id': payment.id
            })
            
        except Exception as e:
            logger.error(f"创建支付订单失败: {str(e)}")
            return ResponseUtil.error(data={
                'success': False,
                'error': str(e)
            }, errors=status.HTTP_400_BAD_REQUEST)


class PaymentView(APIView):
    """支付相关接口"""

    @extend_schema(
        responses=PaymentSerializer(many=True)
    )
    def get(self, request):
        """获取支付记录列表"""
        payments = Payment.objects.filter(user=request.user, is_delete=False)
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=PaymentCreateSerializer,
        responses={
            201: PaymentSerializer,
            400: {
                "description": "参数错误",
                "examples": {
                    "application/json": {
                        "field": ["错误信息"]
                    }
                }
            }
        }
    )
    def post(self, request):
        """创建支付记录"""
        serializer = PaymentCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentDetailView(APIView):
    """支付详情接口"""

    @extend_schema(
        responses=PaymentSerializer
    )
    def get(self, request, pk):
        """获取支付详情"""
        payment = get_object_or_404(Payment, pk=pk, user=request.user, is_delete=False)
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)

    @extend_schema(
        responses={
            200: {
                "description": "支付处理结果",
                "examples": {
                    "application/json": {
                        "success": True,
                        "payment_url": "https://example.com/pay/123",
                        "params": {}
                    }
                }
            },
            400: {
                "description": "支付状态不正确",
                "examples": {
                    "application/json": {
                        "error": "支付订单状态不正确，无法处理"
                    }
                }
            },
            500: {
                "description": "服务器错误",
                "examples": {
                    "application/json": {
                        "error": "具体错误信息"
                    }
                }
            }
        }
    )
    def post(self, request, pk):
        """处理支付"""
        payment = get_object_or_404(Payment, pk=pk, user=request.user, is_delete=False)
        
        if payment.status != 0:  # 待支付
            return ResponseUtil.custom_response(
                code=status.HTTP_400_BAD_REQUEST,
                data={'error': '支付订单状态不正确，无法处理'}
            )
        
        try:
            payment_data = PaymentService.process_payment(payment)
            return Response(payment_data)
        except Exception as e:
            return ResponseUtil.custom_response(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                data={'error': str(e)}
            )


class PaymentNotificationView(APIView):
    """
    统一支付通知接口
    支持多种支付方式（支付宝、微信支付等）的异步通知处理
    通过payment_method参数区分不同的支付方式
    """
    permission_classes = [AllowAny]  # 支付回调不需要认证

    def post(self, request, payment_method):
        """
        处理支付通知
        :param payment_method: 支付方式 (alipay, wechat, bank)
        """
        logger.info(f"收到{payment_method}支付通知")
        
        # 根据支付方式路由到不同的处理函数
        if payment_method == 'alipay':
            return self._handle_alipay_notification(request)
        elif payment_method == 'wechat':
            return self._handle_wechat_notification(request)
        elif payment_method == 'bank':
            return self._handle_bank_notification(request)
        else:
            logger.error(f"不支持的支付方式: {payment_method}")
            return Response({'error': f'Unsupported payment method: {payment_method}'},
                           status=status.HTTP_400_BAD_REQUEST)

    def _handle_alipay_notification(self, request):
        """处理支付宝异步通知"""
        try:
            # 1. 获取并验证基础参数
            data = request.POST.dict()
            signature = data.pop('sign', None)

            if not signature:
                logger.error("支付宝异步通知缺少签名参数")
                return Response("fail - missing signature", status=status.HTTP_400_BAD_REQUEST)

            # 2. 初始化支付宝（使用生产环境配置）
            alipay = AliPay(
                appid=settings.ALIPAY_CONFIG['appid'],
                app_notify_url=settings.ALIPAY_PRODUCTION_NOTIFY_URL,  # 使用生产环境通知地址
                app_private_key_string=open(settings.ALIPAY_CONFIG['app_private_key_path']).read(),
                alipay_public_key_string=open(settings.ALIPAY_CONFIG['alipay_public_key_path']).read(),
                sign_type=settings.ALIPAY_CONFIG['sign_type'],
                debug=False  # 生产环境关闭调试模式
            )

            # 3. 验证签名和交易状态
            if not alipay.verify(data, signature):
                logger.error(f"签名验证失败 | 原始数据: {data} | 签名: {signature}")
                return Response("fail - invalid signature", status=status.HTTP_400_BAD_REQUEST)

            trade_status = data.get('trade_status')
            if trade_status not in ('TRADE_SUCCESS', 'TRADE_FINISHED'):
                logger.warning(f"未处理的交易状态: {trade_status} | 订单: {data.get('out_trade_no')}")
                return Response("fail - invalid trade status", status=status.HTTP_400_BAD_REQUEST)

            # 4. 获取订单信息
            out_trade_no = data.get('out_trade_no')
            trade_no = data.get('trade_no')  # 支付宝交易号
            total_amount = float(data.get('total_amount', 0))

            try:
                order = Order.objects.get(order_no=out_trade_no)
            except Order.DoesNotExist:
                logger.error(f"订单不存在 | 订单号: {out_trade_no}")
                return Response("fail - order not found", status=status.HTTP_404_NOT_FOUND)

            # 5. 处理用户积分和VIP
            user = order.user
            # 获取用户信息
            if user:
                # 获取订单关联产品的 points
                product_points = order.product.points

                # 检查商品的 method 字段是否为 vip1
                if order.product.method == 'vip1':
                    start_time = timezone.now()
                    if UserVIP.objects.filter(user=user, is_active=1).exists():
                        user_vip = UserVIP.objects.get(user=user)
                        user_vip.end_time = user_vip.end_time + relativedelta(months=1)
                        user_vip.save()
                    else:
                        end_time = start_time + relativedelta(months=1)
                        UserVIP.objects.create(
                            user=user,
                            start_time=start_time,
                            end_time=end_time,
                            level='vip_basic',
                        )
                    user.vip_points += product_points
                    user.save()
                elif order.product.method == 'vip2':
                    start_time = timezone.now()
                    if UserVIP.objects.filter(user=user, is_active=1).exists():
                        user_vip = UserVIP.objects.get(user=user)
                        user_vip.end_time = user_vip.end_time + relativedelta(months=6)
                        user_vip.save()
                    else:
                        end_time = start_time + relativedelta(months=6)
                        UserVIP.objects.create(
                            user=user,
                            start_time=start_time,
                            end_time=end_time,
                            level='vip_basic',
                        )
                    user.vip_points += product_points
                    user.save()
                elif order.product.method == 'vip3':
                    start_time = timezone.now()
                    if UserVIP.objects.filter(user=user, is_active=1).exists():
                        user_vip = UserVIP.objects.get(user=user)
                        user_vip.end_time = user_vip.end_time + relativedelta(months=12)
                        user_vip.save()
                    else:
                        end_time = start_time + relativedelta(months=12)
                        UserVIP.objects.create(
                            user=user,
                            start_time=start_time,
                            end_time=end_time,
                            level='vip_basic',
                        )
                    user.vip_points += product_points
                    user.save()
                else:
                    user.points += product_points
                    user.save()
            else:
                return ResponseUtil.error(message='用户不存在')

            logger.info(f"支付宝支付成功通知 | 订单: {out_trade_no} | 金额: {total_amount} | 支付宝交易号: {trade_no}")

            # 6. 更新支付状态
            return self._update_payment_status(
                out_trade_no=out_trade_no,
                transaction_id=trade_no,
                amount=total_amount,
                raw_data=data
            )

        except Exception as e:
            logger.error(f"处理支付宝异步通知异常: {str(e)}", exc_info=True)
            return Response(f"error - {str(e)}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_wechat_notification(self, request):
        """处理微信支付异步通知"""
        try:
            # 获取请求头和请求体
            headers = request.headers
            body = request.data

            logger.info(f"接收到微信支付通知: {body}")

            # 解密通知数据
            decrypted_data = PaymentService.decrypt_wechat_notification(body)
            if not decrypted_data:
                logger.error("微信支付通知解密失败")
                return HttpResponse("FAIL", status=400)

            # 验证通知合法性
            if not PaymentService.verify_wechat_notification(headers, body, decrypted_data):
                logger.error("微信支付通知验证失败")
                return HttpResponse("FAIL", status=400)

            # 获取商户订单号和交易流水号
            out_trade_no = decrypted_data.get('out_trade_no')
            transaction_id = decrypted_data.get('transaction_id')

            # 计算金额，微信支付金额单位为分，需要除以100转为元
            total_fee = decrypted_data.get('amount', {}).get('total', 0)
            total_amount = float(total_fee) / 100  # 转换为元

            logger.info(f"微信支付成功通知 | 订单: {out_trade_no} | 金额: {total_amount} | 微信交易号: {transaction_id}")

            # 使用统一的方法更新支付状态
            response = self._update_payment_status(
                out_trade_no=out_trade_no,
                transaction_id=transaction_id,
                amount=total_amount,
                raw_data=decrypted_data
            )

            # 微信支付要求返回特定格式的响应
            if response.status_code == 200:
                return HttpResponse('{"code": "SUCCESS", "message": "成功"}')
            else:
                return HttpResponse('{"code": "FAIL", "message": "失败"}', status=response.status_code)

        except Exception as e:
            logger.error(f"处理微信支付通知异常: {str(e)}", exc_info=True)
            return HttpResponse('{"code": "FAIL", "message": "系统错误"}', status=500)

    def _handle_bank_notification(self, request):
        """处理银行卡支付异步通知"""
        # 银行卡支付处理逻辑根据实际情况实现
        try:
            data = request.data

            # 这里添加银行卡支付通知验证逻辑
            client = BankPayClient()
            if not client.verify_notification(data):
                logger.error("银行卡支付通知验证失败")
                return Response({"error": "Invalid bank notification"}, status=400)

            # 获取订单号
            out_trade_no = data.get('reference')
            transaction_id = data.get('bank_transaction_id')
            total_amount = float(data.get('amount', 0))

            logger.info(f"银行卡支付成功通知 | 订单: {out_trade_no} | 金额: {total_amount} | 银行交易号: {transaction_id}")

            # 使用统一的方法更新支付状态
            return self._update_payment_status(
                out_trade_no=out_trade_no,
                transaction_id=transaction_id,
                amount=total_amount,
                raw_data=data
            )

        except Exception as e:
            logger.error(f"处理银行卡支付通知异常: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=500)

    def _update_payment_status(self, out_trade_no, transaction_id, amount, raw_data):
        """
        统一处理支付状态更新
        """
        try:
            with transaction.atomic():
                # 查询订单和支付信息
                order = Order.objects.get(order_no=out_trade_no)
                payment = Payment.objects.get(order=order)

                # 验证订单金额是否匹配
                if abs(float(order.actual_amount) - amount) > 0.01:  # 允许0.01元的误差
                    logger.error(f"订单金额不匹配 | 订单金额: {order.actual_amount} | 支付金额: {amount}")
                    return Response({"error": "Amount mismatch"}, status=status.HTTP_400_BAD_REQUEST)

                # 调用支付服务处理状态更新及后续业务逻辑
                PaymentService.update_payment_status(
                    payment=payment,
                    status=1,  # 已支付
                    transaction_id=transaction_id,
                    raw_response=raw_data
                )

                logger.info(f"订单支付状态更新成功 | 订单: {out_trade_no}")
                return Response({"status": "success"})

        except Order.DoesNotExist:
            logger.error(f"订单不存在 | 订单: {out_trade_no}")
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        except Payment.DoesNotExist:
            logger.error(f"支付记录不存在 | 订单: {out_trade_no}")
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"处理订单异常 | 订单: {out_trade_no} | 异常: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RefundView(APIView):
    """退款相关接口"""

    @extend_schema(
        responses=RefundSerializer(many=True))
    def get(self, request):
        """获取退款记录列表"""
        refunds = Refund.objects.filter(payment__user=request.user, is_delete=False)
        serializer = RefundSerializer(refunds, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=RefundCreateSerializer,
        responses={
            201: RefundSerializer,
            400: {
                "description": "退款申请失败",
                "examples": {
                    "application/json": {
                        "error": "只有已支付的订单才能退款"
                    }
                }
            }
        }
    )
    def post(self, request):
        """创建退款申请"""
        serializer = RefundCreateSerializer(data=request.data)
        if serializer.is_valid():
            payment = get_object_or_404(
                Payment, 
                pk=request.data.get('payment'),
                user=request.user
            )
            
            if payment.status != 1:  # 已支付
                return Response(
                    {'error': '只有已支付的订单才能退款'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if float(request.data.get('amount', 0)) > float(payment.amount):
                return Response(
                    {'error': '退款金额不能大于支付金额'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer.save(payment=payment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RefundDetailView(APIView):
    """退款详情接口"""

    @extend_schema(
        responses=RefundSerializer
    )
    def get(self, request, pk):
        """获取退款详情"""
        refund = get_object_or_404(Refund, pk=pk, payment__user=request.user, is_delete=False)
        serializer = RefundSerializer(refund)
        return Response(serializer.data)

    @extend_schema(
        responses={
            200: {
                "description": "退款处理结果",
                "examples": {
                    "application/json": {
                        "success": True,
                        "transaction_id": "123456",
                        "raw_response": {}
                    }
                }
            },
            400: {
                "description": "退款状态不正确",
                "examples": {
                    "application/json": {
                        "error": "退款订单状态不正确，无法处理"
                    }
                }
            },
            500: {
                "description": "服务器错误",
                "examples": {
                    "application/json": {
                        "error": "具体错误信息"
                    }
                }
            }
        }
    )
    def post(self, request, pk):
        """处理退款"""
        refund = get_object_or_404(Refund, pk=pk, payment__user=request.user, is_delete=False)
        
        if refund.status != 0:  # 处理中
            return Response(
                {'error': '退款订单状态不正确，无法处理'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            refund_data = PaymentService.process_refund(refund)
            return Response(refund_data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TestOrderView(APIView):
    """测试订单接口"""

    def post(self, request):
        """创建测试订单"""
        try:
            # 生成订单号
            order_no = f"TEST_{uuid.uuid4().hex[:8]}"
            
            # 创建测试订单
            order = Order.objects.create(
                user=request.user,
                order_no=order_no,
                total_amount=0.01,  # 测试金额1分钱
                actual_amount=0.01,
                status=0,  # 待支付
                payment_method=1,  # 支付宝
                description="测试订单"
            )
            
            return Response({
                'success': True,
                'order_id': order.id,
                'order_no': order.order_no,
                'amount': order.actual_amount
            })
            
        except Exception as e:
            logger.error(f"创建测试订单失败: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class TestPaymentFlowView(APIView):
    """
    测试支付流程完整接口，无需用户登录
    支持测试不同支付方式的完整流程
    """
    permission_classes = []  # 不需要认证

    def post(self, request):
        try:
            # 获取支付方式
            payment_method = request.data.get('payment_method', 1)  # 默认支付宝
            payment_method = int(payment_method)

            # 获取支付金额
            amount = request.data.get('amount', '0.01')  # 默认0.01元
            amount = Decimal(amount)

            # 获取微信支付的参数
            client_type = request.data.get('client_type', 'pc')  # 默认PC端，可选miniprog
            openid = request.data.get('openid')  # 小程序支付需要openid

            if payment_method == 2 and client_type == 'miniprog' and not openid:
                return ResponseUtil.error("微信小程序支付需要提供openid", status=status.HTTP_400_BAD_REQUEST)

            # 1. 创建/获取测试用户
            User = get_user_model()
            test_user, _ = User.objects.get_or_create(
                username='test_payment_user',
                defaults={
                    'email': 'test_payment@example.com',
                    'phone': '13800138000',
                    'userRole': 'user',
                    'points': 100,
                    'role': '0',
                    'isDelete': 0
                }
            )

            # 2. 创建/获取测试商品
            product, _ = Product.objects.get_or_create(
                description="测试商品",
                defaults={
                    'price': amount,
                    'points': 10,
                    'is_delete': False
                }
            )
            # 更新价格为当前请求的价格
            product.price = amount
            product.save()

            # 3. 创建订单和支付记录
            order_service = OrderService()
            order = order_service.create_order(
                user=test_user,
                product=product
            )

            # 4. 创建支付记录
            payment = order_service.create_payment(
                order=order,
                payment_method=payment_method
            )

            # 5. 根据支付方式处理支付
            payment_service = PaymentService()

            payment_kwargs = {}
            if payment_method == 2:  # 微信支付
                payment_kwargs['pay_type'] = client_type
                payment_kwargs['client_ip'] = request.META.get('REMOTE_ADDR')

                if client_type == 'miniprog':
                    payment_kwargs['openid'] = openid
                    payment_kwargs['trade_type'] = 'JSAPI'
                else:
                    payment_kwargs['trade_type'] = 'NATIVE'

            payment_data = payment_service.process_payment(payment, **payment_kwargs)

            if not payment_data.get('success'):
                return ResponseUtil.error(payment_data.get('error', '支付创建失败'))

            # 6. 构建返回结果
            result = {
                'test_info': {
                    'user': {
                        'id': test_user.id,
                        'username': test_user.username
                    },
                    'order': {
                        'id': order.id,
                        'order_no': order.order_no,
                        'amount': str(order.actual_amount)
                    },
                    'payment': {
                        'id': payment.id,
                        'payment_method': payment_method,
                        'payment_method_name': '支付宝' if payment_method == 1 else '微信支付' if payment_method == 2 else '其他'
                    }
                },
                'payment_data': {
                    'payment_url': payment_data.get('pay_url'),
                    'payment_params': payment_data.get('params'),
                    'code_url': payment_data.get('code_url')
                },
                'notification_info': {
                    'notification_url': request.build_absolute_uri('/').rstrip('/') +
                                       f'/api/payments/notification/{payment_method}/',
                    'order_no': order.order_no,
                    'amount': str(order.actual_amount)
                }
            }

            # 7. 添加支付方式特定的返回信息
            if payment_method == 1:  # 支付宝
                result['alipay_info'] = {
                    'payment_url': payment_data.get('pay_url'),
                    'testing_tips': '复制支付链接到浏览器打开，使用沙箱账号支付'
                }
            elif payment_method == 2:  # 微信支付
                if client_type == 'pc':
                    result['wechatpay_info'] = {
                        'code_url': payment_data.get('code_url'),
                        'testing_tips': '使用该code_url生成二维码，用微信扫描支付'
                    }
                else:
                    result['wechatpay_info'] = {
                        'payment_params': payment_data.get('params'),
                        'testing_tips': '将支付参数传递给小程序前端调用wx.requestPayment'
                    }

            return ResponseUtil.success(result, message="测试支付创建成功")

        except Exception as e:
            logger.error(f"测试支付流程失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(f"测试支付失败: {str(e)}")


class TestManualNotificationView(APIView):
    """
    手动模拟支付平台回调通知
    用于开发测试使用
    """
    permission_classes = []  # 不需要认证

    def post(self, request):
        try:
            # 获取参数
            payment_method = request.data.get('payment_method', 1)  # 默认支付宝
            order_no = request.data.get('order_no')
            amount = request.data.get('amount')

            if not order_no:
                return ResponseUtil.error("缺少订单号", status=status.HTTP_400_BAD_REQUEST)

            if not amount:
                return ResponseUtil.error("缺少支付金额", status=status.HTTP_400_BAD_REQUEST)

            # 查找订单和支付记录
            try:
                order = Order.objects.get(order_no=order_no)
                payment = Payment.objects.get(order=order)
            except (Order.DoesNotExist, Payment.DoesNotExist):
                return ResponseUtil.error(f"找不到订单 {order_no}", status=status.HTTP_404_NOT_FOUND)

            # 模拟支付平台回调
            payment_service = PaymentService()

            # 根据支付方式模拟不同的回调内容
            if int(payment_method) == 1:  # 支付宝
                # 模拟支付宝通知数据结构
                notify_data = {
                    'out_trade_no': order_no,
                    'trade_no': f'alipay_test_{int(time.time())}',
                    'total_amount': str(amount),
                    'trade_status': 'TRADE_SUCCESS',
                    'gmt_payment': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                # 更新支付状态
                result = payment_service.update_payment_status(
                    payment=payment,
                    trade_no=notify_data['trade_no'],
                    payment_status='success',
                    payment_amount=Decimal(notify_data['total_amount'])
                )

            elif int(payment_method) == 2:  # 微信支付
                # 模拟微信支付通知数据结构
                notify_data = {
                    'out_trade_no': order_no,
                    'transaction_id': f'wxpay_test_{int(time.time())}',
                    'amount': {
                        'total': int(Decimal(amount) * 100),  # 微信金额单位为分
                        'currency': 'CNY'
                    },
                    'trade_state': 'SUCCESS',
                    'success_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                # 更新支付状态
                result = payment_service.update_payment_status(
                    payment=payment,
                    trade_no=notify_data['transaction_id'],
                    payment_status='success',
                    payment_amount=Decimal(amount)
                )

            else:
                return ResponseUtil.error(f"不支持的支付方式: {payment_method}", status=status.HTTP_400_BAD_REQUEST)

            if result.get('success'):
                return ResponseUtil.success({
                    'order_no': order_no,
                    'status': 'success',
                    'notify_data': notify_data
                }, message="模拟支付通知处理成功")
            else:
                return ResponseUtil.error(result.get('error', '模拟支付通知处理失败'))

        except Exception as e:
            logger.error(f"模拟支付通知失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(f"模拟支付通知失败: {str(e)}")




# 查询所有商品套餐
class getProduct1(APIView):
    """测试支付流程接口"""
    # permission_classes = [AllowAny]

    def get(self, request):
        try:
            # # 查询所有订单
            orders = Product.objects.filter(is_delete=False)
            # # 将查询结果转换为字典列表
            order_list = [model_to_dict(order) for order in orders]

            return ResponseUtil.success( data=order_list,message="查询成功")
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

class ProductDeleteView(APIView):
    # permission_classes = [AllowAny]

    """
    软删除 Example 实例的视图，通过修改 is_deleted 字段实现
    """
    def delete(self, request, pk):
        try:
            # 尝试获取指定主键的 Example 实例
            example = Product.objects.get(pk=pk, is_delete=False)
            # 将 is_deleted 字段设置为 True
            example.is_delete = True
            example.save()
            return ResponseUtil.success()

        except Product.DoesNotExist:
            return ResponseUtil.error()


# 后台修改商品
class UpdateProductView(APIView):
    """修改Product模型的接口"""
    # permission_classes = [AllowAny]  # 根据需求设置权限

    def put(self, request, pk):
        """更新Product对象"""
        try:
            # 获取要更新的Product对象
            product = get_object_or_404(Product, pk=pk)
            # 初始化序列化器
            serializer = ProductSerializer(product, data=request.data, partial=True)
            print(serializer)
            if serializer.is_valid():
                # 保存更新后的对象
                serializer.save()
                return ResponseUtil.success(data=serializer.data)
            return ResponseUtil.error()
        except Exception as e:
            logger.error(f"更新Product对象失败: {str(e)}")
            return ResponseUtil.error(description = str(e))


class TestPaymentSuccessView(APIView):
    """
    测试支付流程
    1. 创建测试用户
    2. 创建测试商品
    3. 创建测试订单
    4. 创建支付记录
    5. 返回支付宝支付链接
    """

    def post(self, request):
        """
        测试完整的支付流程
        """
        try:
            # 1. 创建测试用户
            User = get_user_model()
            test_user, _ = User.objects.get_or_create(
                username='test_user_payment',
                defaults={
                    'email': 'test_payment@example.com',
                    'phone': '13800138001',
                    'userRole': 'user',
                    'points': 100,  # 初始积分
                    'role': '0',    # 初始月卡状态
                    'isDelete': 0
                }
            )

            # 2. 创建测试商品
            product = Product.objects.create(
                price=99,           # 商品价格
                points=50,            # 商品种子值
                description="测试商品"
            )

            # 3. 创建测试订单
            order = Order.objects.create(
                user=test_user,
                order_no=f"TEST_ORDER_{int(time.time())}",
                total_amount=product.price,
                actual_amount=product.price,
                product=product,
                payment_method=1,  # 支付宝
                status=0,  # 待支付
                remark="支付测试",
                receiver_name="测试用户",
                receiver_phone="13800138001",
                receiver_address="测试地址"
            )

            # 4. 创建支付记录
            payment = Payment.objects.create(
                user=test_user,
                order=order,
                amount=order.actual_amount,
                payment_method=1,  # 支付宝
                status=0,  # 待支付
                description="测试商品支付"
            )

            # 5. 调用支付服务处理支付
            payment_service = PaymentService()
            payment_data = payment_service.process_payment(payment)
            
            if not payment_data.get('success'):
                return Response({
                    'error': payment_data.get('error', '支付创建失败')
                }, status=status.HTTP_400_BAD_REQUEST)

            # 6. 返回支付信息
            return Response({
                'message': '请使用以下链接完成支付',
                'payment_info': {
                    'payment_url': payment_data.get('pay_url'),
                    'order_info': {
                        'order_no': order.order_no,
                        'amount': str(order.actual_amount),
                        'description': order.remark,
                        'user_info': {
                            'username': test_user.username,
                            'phone': test_user.phone
                        }
                    }
                }
            })

        except Exception as e:
            logger.error(f"测试支付流程失败: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WeChatPayView(APIView):
    """
    微信小程序支付视图
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        生成微信小程序支付参数
        """
        try:
            # 获取微信用户openid
            openid = request.data.get('openid')
            if not openid:
                return ResponseUtil.error("缺少微信openid")

            # 获取商品和数量
            product_id = request.data.get('product_id')
            if not product_id:
                return ResponseUtil.error("缺少商品ID")

            # 创建订单
            product = Product.objects.filter(id=product_id).first()
            if not product:
                return ResponseUtil.error("商品不存在")

            # 创建订单和支付记录
            order_service = OrderService()
            order = order_service.create_order(
                user=request.user,
                product=product,
                amount=request.data.get('custom_amount')
            )

            # 创建支付记录
            payment = order_service.create_payment(
                order=order,
                payment_method=2  # 2: 微信支付
            )

            # 生成微信小程序支付参数
            payment_service = PaymentService()
            payment_data = payment_service.process_wechat_miniprog_payment(
                payment,
                openid=openid,
                trade_type='JSAPI',
                client_ip=request.META.get('REMOTE_ADDR')
            )

            if not payment_data.get('success'):
                return ResponseUtil.error(payment_data.get('error', '支付创建失败'))

            return ResponseUtil.success({
                'order_id': order.id,
                'order_no': order.order_no,
                'amount': str(order.actual_amount),
                'payment_method': 2,
                'payment_params': payment_data.get('params'),
                'status': 'pending'
            }, message="支付创建成功")

        except Exception as e:
            logger.error(f"微信支付创建失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(f"支付创建失败: {str(e)}")


class WeChatPayViewPC(APIView):
    """
    微信PC端支付视图
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        生成微信PC端支付链接
        """
        try:
            # 获取商品和数量
            product_id = request.data.get('product_id')
            if not product_id:
                return ResponseUtil.error("缺少商品ID")

            # 创建订单
            product = Product.objects.filter(id=product_id).first()
            if not product:
                return ResponseUtil.error("商品不存在")

            # 创建订单和支付记录
            order_service = OrderService()
            order = order_service.create_order(
                user=request.user,
                product=product,
                amount=request.data.get('custom_amount')
            )

            # 创建支付记录
            payment = order_service.create_payment(
                order=order,
                payment_method=2  # 2: 微信支付
            )

            # 生成微信PC支付参数
            payment_service = PaymentService()
            payment_data = payment_service.process_wechat_pc_payment(
                payment,
                trade_type='NATIVE',
                client_ip=request.META.get('REMOTE_ADDR')
            )

            if not payment_data.get('success'):
                return ResponseUtil.error(payment_data.get('error', '支付创建失败'))

            return ResponseUtil.success({
                'order_id': order.id,
                'order_no': order.order_no,
                'amount': str(order.actual_amount),
                'payment_method': 2,
                'payment_url': payment_data.get('pay_url'),
                'code_url': payment_data.get('code_url'),
                'status': 'pending'
            }, message="支付创建成功")

        except Exception as e:
            logger.error(f"微信PC支付创建失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(f"支付创建失败: {str(e)}")


# 查询所有订单
class getOrder(APIView):
    """测试支付流程接口"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            
            # 获取分页参数                           
            page = request.GET.get('page', 1)
            page_size = request.GET.get('page_size', 10)
            # status1 = request.GET.get('status', "1")

            if request.GET.get('user_id'):
                print("用户id：",request.GET.get('user_id'))                          
                user = SysUser.objects.get(id=request.GET.get('user_id'))
            else:
                user = request.user
            
            # 检查用户角色
            if user.userRole == 'admin':
                # 管理员获取所有订单
                # records = Order.objects.all().order_by('-create_time')
                records = Order.objects.filter(status=1).order_by('-create_time')
            else:
                # 普通用户获取自己的订单
                records = Order.objects.filter(user_id=user.id).order_by('-create_time')
            
            # 分页处理
            paginator = Paginator(records, page_size)
            try:
                page_obj = paginator.page(page)
            except Exception:
                return ResponseUtil.error(message="请求的页码不存在")
            result = []
            for record in page_obj.object_list:
                try:
                    if record.user_id:
                        user = SysUser.objects.get(id=record.user_id)
                        username = user.username
                    else:
                        username = ""
                except Exception:
                    username = ""

                print(username)
                record_data = {
                    'id': record.id,
                    'user_id': record.user_id,  # 添加用户存在检查
                    'user_name': username,  # 添加用户存在检查
                    'order_no': record.order_no,
                    'total_amount': record.total_amount,
                    'actual_amount': record.actual_amount,
                    'product': record.product.description,
                    'status': record.status,
                    'payment_method': record.payment_method,
                    'payment_time': record.payment_time,
                    'create_time': record.create_time, 
                    'remark': record.remark,
                }
                result.append(record_data)
            return ResponseUtil.success(data={
                'data': result,
                'total': paginator.count,
                'page': page,
                'page_size': page_size
            }, message="查询成功")
        except Exception as e:
            return ResponseUtil.error(message = str(e))

# 后台系统查询所有商品套餐
class getProduct(APIView):
    """测试支付流程接口"""
    # permission_classes = [AllowAny]

    def get(self, request):
        try:
            # # 查询所有订单
            orders = Product.objects.filter(is_delete=False)
            # # 将查询结果转换为字典列表
            order_list = [model_to_dict(order) for order in orders]
            
            return ResponseUtil.success( data=order_list,message="查询成功")
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


# 用户查询所有商品套餐
class userProduct(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            method = request.query_params.get('method', "pp")
            user = request.user
            # 原有逻辑
            if user.openid:
                products = Product.objects.filter(way__in=[2, 3], is_delete=False, method__contains=method)
            else:
                products = Product.objects.filter(way__in=[1,3], is_delete=False, method__contains=method)

            print(products)

            # 新增逻辑：根据用户信息查询订单表
            user_orders = Order.objects.filter(user=user, is_delete=False,status=1)
            vip_product_ids = []
            for order in user_orders:
                if order.product and "vip" in order.product.method:
                    vip_product_ids.append(order.product.id)
            print(vip_product_ids)

            additional_products = Product.objects.none()
            if not vip_product_ids and method == "vip" and user.openid:
                # 查询 way 是 0 且在 vip_product_ids 中的商品
                additional_products = Product.objects.filter(
                    # id__in=vip_product_ids,
                    way=0,
                    # is_delete=False,
                )
            print(additional_products)

            # 合并结果
            all_products = (additional_products | products ).distinct().order_by('price')
            print(all_products)

            serializer = ProductSerializer(all_products, many=True)
            return ResponseUtil.success(data=serializer.data, message="查询成功")
        except Exception as e:
            return ResponseUtil.error(message=str(e))

# 删除商品接口
class ProductDeleteView(APIView):
    # permission_classes = [AllowAny]

    """
    软删除 Example 实例的视图，通过修改 is_deleted 字段实现
    """
    def delete(self, request, pk):
        try:
            # 尝试获取指定主键的 Example 实例
            example = Product.objects.get(pk=pk, is_delete=False)
            # 将 is_deleted 字段设置为 True
            example.is_delete = True
            example.save()
            return ResponseUtil.success()

        except Product.DoesNotExist:
            return ResponseUtil.error()


# 后台修改商品
class UpdateProductView(APIView):
    """修改Product模型的接口"""
    # permission_classes = [AllowAny]  # 根据需求设置权限

    def put(self, request, pk):
        """更新Product对象"""
        try:
            # 获取要更新的Product对象
            product = get_object_or_404(Product, pk=pk)
            # 初始化序列化器
            serializer = ProductSerializer(product, data=request.data, partial=True)
            print(serializer)
            if serializer.is_valid():
                # 保存更新后的对象
                serializer.save()
                return ResponseUtil.success(data=serializer.data)
            return ResponseUtil.error()
        except Exception as e:
            logger.error(f"更新Product对象失败: {str(e)}")
            return ResponseUtil.error(description = str(e))


class TestPaymentSuccessView(APIView):
    """
    测试支付流程
    1. 创建测试用户
    2. 创建测试商品
    3. 创建测试订单
    4. 创建支付记录
    5. 返回支付宝支付链接
    """

    def post(self, request):
        """
        测试完整的支付流程
        """
        try:
            # 1. 创建测试用户
            User = get_user_model()
            test_user, _ = User.objects.get_or_create(
                username='test_user_payment',
                defaults={
                    'email': 'test_payment@example.com',
                    'phone': '13800138001',
                    'userRole': 'user',
                    'points': 100,  # 初始积分
                    'role': '0',    # 初始月卡状态
                    'isDelete': 0
                }
            )

            # 2. 创建测试商品
            product = Product.objects.create(
                price=99,           # 商品价格
                points=50,            # 商品种子值
                description="测试商品"
            )

            # 3. 创建测试订单
            order = Order.objects.create(
                user=test_user,
                order_no=f"TEST_ORDER_{int(time.time())}",
                total_amount=product.price,
                actual_amount=product.price,
                product=product,
                payment_method=1,  # 支付宝
                status=0,  # 待支付
                remark="支付测试",
                receiver_name="测试用户",
                receiver_phone="13800138001",
                receiver_address="测试地址"
            )

            # 4. 创建支付记录
            payment = Payment.objects.create(
                user=test_user,
                order=order,
                amount=order.actual_amount,
                payment_method=1,  # 支付宝
                status=0,  # 待支付
                description="测试商品支付"
            )

            # 5. 调用支付服务处理支付
            payment_service = PaymentService()
            payment_data = payment_service.process_payment(payment)
            
            if not payment_data.get('success'):
                return Response({
                    'error': payment_data.get('error', '支付创建失败')
                }, status=status.HTTP_400_BAD_REQUEST)

            # 6. 返回支付信息
            return Response({
                'message': '请使用以下链接完成支付',
                'payment_info': {
                    'payment_url': payment_data.get('pay_url'),
                    'order_info': {
                        'order_no': order.order_no,
                        'amount': str(order.actual_amount),
                        'description': order.remark,
                        'user_info': {
                            'username': test_user.username,
                            'phone': test_user.phone
                        }
                    }
                }
            })

        except Exception as e:
            logger.error(f"测试支付流程失败: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductPaymentView(APIView):
    """
    商品支付视图
    支持微信JSAPI支付(小程序/H5)
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: {
                "description": "支付创建成功",
                "examples": {
                    "application/json": {
                        "order_id": 1,
                        "order_no": "ORDER_123456",
                        "amount": "99.00",
                        "payment_method": 2,
                        "payment_url": "https://example.com/pay/123",
                        "payment_params": {},
                        "status": "pending"
                    }
                }
            },
            400: {
                "description": "支付创建失败",
                "examples": {
                    "application/json": {
                        "error": "请选择商品"
                    }
                }
            },
            500: {
                "description": "服务器错误",
                "examples": {
                    "application/json": {
                        "error": "具体错误信息"
                    }
                }
            }
        },
        parameters=[
            OpenApiParameter(
                name='product_id',
                description='商品ID',
                required=True,
                type=int,
                location=OpenApiParameter.QUERY
            ),
            OpenApiParameter(
                name='payment_method',
                description='支付方式(1:支付宝 2:微信支付 3:银行卡)',
                required=False,
                type=int,
                location=OpenApiParameter.QUERY,
                default=1
            ),
            OpenApiParameter(
                name='custom_amount',
                description='exchange类型商品的自定义支付金额',
                required=False,
                type=float,
                location=OpenApiParameter.QUERY
            ),
            OpenApiParameter(
                name='openid',
                description='微信JSAPI支付需要的openid',
                required=False,
                type=str,
                location=OpenApiParameter.QUERY
            )
        ]
    )
    def post(self, request):
        try:
            # 1. 获取请求参数
            product_id = request.data.get('product_id')
            payment_method = request.data.get('payment_method', 1)
            custom_amount = request.data.get('custom_amount')  # 新增参数
            openid = request.data.get('openid')

            if not product_id:
                return Response({
                    'error': '请选择商品'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return ResponseUtil.error("商品不存在", status=status.HTTP_400_BAD_REQUEST)

            # 3. 特殊处理exchange类型商品
            if product.method == "exchange":
                if not custom_amount or float(custom_amount) <= 0:
                    return ResponseUtil.error("兑换类型商品需指定有效金额", status=status.HTTP_400_BAD_REQUEST)

                # 验证金额是否满足最小单位（如1元兑换10积分）
                if float(custom_amount) < (1 / product.points):  # 假设product.points是兑换率（如10表示1元兑10积分）
                    return ResponseUtil.error(f"金额不能小于{1 / product.points}元",
                                            status=status.HTTP_400_BAD_REQUEST)

                actual_amount = Decimal(custom_amount).quantize(Decimal('0.01'))
            else:
                actual_amount = product.price

            # 验证支付方式
            if payment_method not in [1, 2, 3]:  # 1:支付宝 2:微信支付 3:银行卡
                return Response({
                    'error': '不支持的支付方式'
                }, status=status.HTTP_400_BAD_REQUEST)

            # JSAPI支付必须提供openid
            if payment_method == 2 and request.data.get('trade_type') == 'JSAPI' and not openid:
                return Response({
                    'error': '微信JSAPI支付需要提供openid'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 2. 创建订单
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                order_no=f"ORDER_{int(time.time())}",
                total_amount=actual_amount,
                actual_amount=actual_amount,
                product=product,
                payment_method=payment_method,
                status=0,  # 待支付
                remark=product.description,
                receiver_name=request.data.get('receiver_name', ''),
                receiver_phone=request.data.get('receiver_phone', ''),
                receiver_address=request.data.get('receiver_address', '')
            )

            # 3. 创建支付记录
            payment = Payment.objects.create(
                user=request.user if request.user.is_authenticated else None,
                order=order,
                amount=order.actual_amount,
                payment_method=payment_method,
                status=0,  # 待支付
                description=product.description
            )

            # 4. 调用支付服务处理支付
            payment_service = PaymentService()

            # 根据支付方式处理
            if payment_method == 1:  # 支付宝
                # 初始化支付宝（使用生产环境配置）
                alipay = AliPay(
                    appid=settings.ALIPAY_CONFIG['appid'],
                    app_notify_url=settings.ALIPAY_PRODUCTION_NOTIFY_URL,
                    app_private_key_string=open(settings.ALIPAY_CONFIG['app_private_key_path']).read(),
                    alipay_public_key_string=open(settings.ALIPAY_CONFIG['alipay_public_key_path']).read(),
                    sign_type=settings.ALIPAY_CONFIG['sign_type'],
                    debug=False  # 生产环境关闭调试模式
                )

                # 生成支付宝支付链接
                order_string = alipay.api_alipay_trade_page_pay(
                    out_trade_no=order.order_no,
                    total_amount=str(order.actual_amount),
                    subject=order.remark,
                    return_url=settings.ALIPAY_PRODUCTION_RETURN_URL,
                    notify_url=settings.ALIPAY_PRODUCTION_NOTIFY_URL
                )

                # 构建支付链接
                payment_url = f"{settings.ALIPAY_PRODUCTION_GATEWAY}?{order_string}"
                payment_data = {
                    'success': True,
                    'pay_url': payment_url
                }

            elif payment_method == 2:  # 微信支付
                # 微信支付支持传递额外参数
                payment_kwargs = {
                    'pay_type': request.data.get('client_type', 'miniprog'),
                    'trade_type': request.data.get('trade_type', 'JSAPI'),
                    'client_ip': request.META.get('REMOTE_ADDR')
                }

                if payment_kwargs['pay_type'] == 'miniprog':
                    if not openid:
                        return ResponseUtil.error("微信小程序支付需要提供openid", status=status.HTTP_400_BAD_REQUEST)
                    payment_kwargs['openid'] = openid

                payment_data = payment_service.process_payment(payment, **payment_kwargs)

            else:  # 银行卡支付
                payment_data = payment_service.process_payment(payment)

            if not payment_data.get('success'):
                return ResponseUtil.error(payment_data.get('error', '支付创建失败'))

            # 通用处理
            response_data = {
                'order_id': order.id,
                'order_no': order.order_no,
                'amount': str(order.actual_amount),
                'payment_method': payment_method,
                'status': 'pending',
                'exchange_rate': product.points if product.method == "exchange" else None  # 返回兑换率
            }

            # 根据支付方式返回不同的参数
            if payment_method == 1:  # 支付宝
                response_data['payment_url'] = payment_data.get('pay_url')
            elif payment_method == 2:  # 微信支付
                response_data['payment_url'] = payment_data.get('pay_url')
                response_data['payment_params'] = payment_data.get('params')

            return ResponseUtil.success(response_data, message="支付创建成功")

        except Exception as e:
            logger.error(f"商品支付失败: {str(e)}", exc_info=True)
            return ResponseUtil.error("支付处理异常")


class WeChatPayNotifyView(APIView):
    """
    微信支付通知接口
    """

    def post(self, request):
        try:
            # 获取通知数据
            from wechatpy.pay import parse_payment_result
            result = parse_payment_result(request.body)

            # 验证通知合法性
            client = WeChatPayClient()
            if not client.verify_notification(result):
                return HttpResponse("FAIL", status=400)

            # 获取商户订单号
            out_trade_no = result.get('out_trade_no')
            if not out_trade_no:
                return HttpResponse("FAIL", status=400)

            # 获取支付记录
            try:
                payment = Payment.objects.get(order__order_no=out_trade_no)
            except Payment.DoesNotExist:
                return HttpResponse("FAIL", status=404)

            # 更新支付状态
            PaymentService.update_payment_status(
                payment=payment,
                status=1,  # 已支付
                transaction_id=result.get('transaction_id'),
                raw_response=result
            )

            return HttpResponse("SUCCESS")

        except Exception as e:
            logger.error(f"处理微信支付通知失败: {str(e)}", exc_info=True)
            return HttpResponse("FAIL", status=500)


class WeChatAuthView(APIView):
    """微信授权获取openid"""


    def get(self, request):
        # 配置从settings中读取
        app_id = settings.WECHAT_APP_ID
        app_secret = settings.WECHAT_APP_SECRET
        redirect_uri = settings.WECHAT_REDIRECT_URI

        code = request.query_params.get('code')
        if not code:
            # 第一步：跳转到微信授权页面
            oauth = WeChatOAuth(app_id, app_secret, redirect_uri, scope='snsapi_base')
            auth_url = oauth.authorize_url
            return Response({'auth_url': auth_url})

        try:
            # 第二步：通过code获取openid
            oauth = WeChatOAuth(app_id, app_secret, redirect_uri)
            access_info = oauth.fetch_access_token(code)
            openid = access_info['openid']

            # 可以将openid存储在session或返回给前端
            request.session['wechat_openid'] = openid

            return Response({
                'success': True,
                'openid': openid
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=400)

from datetime import time as datetime_time  # 避免与导入的time模块冲突

# 后台营业额数据
class daily_revenue_last_seven_days(APIView):
    """修改Product模型的接口"""
    # permission_classes = [AllowAny]  # 根据需求设置权限

    def get(self, request):
        try:
                    # 获取当前日期和时间
            # 获取当前日期和时间
            now = timezone.now()  # 使用timezone确保时区一致
            today = now.date()
            
            # 计算过去7天的日期范围（包含今天完整24小时）
            seven_days_ago = (now - timedelta(days=6)).date()
            
            print(f"查询时间范围: {seven_days_ago} 00:00:00 到 {today} 23:59:59")
            
            # 修复：使用datetime.time.min和datetime.time.max
            
            orders = Order.objects.filter(
                create_time__gte=datetime.combine(seven_days_ago, datetime_time.min),  # 起始日00:00:00
                create_time__lte=datetime.combine(today, datetime_time.max),          # 结束日23:59:59
                status=1
            )
            print(f"查询到 {orders.count()} 条记录")
            print("订单数据",orders)
            # 计算总金额
            total_revenue = sum(order.actual_amount for order in orders)
            # 准备返回数据
            data = []
            for i in range(7):
                date = today - timedelta(days=i)
                # 计算该日期的订单金额
                date_revenue = sum(order.actual_amount for order in orders if order.create_time.date() == date)
                data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'revenue': date_revenue 
                })
            # 返回数据
            return ResponseUtil.success(data=data)
        except Exception as e:
            return JsonResponse({'status': 'error','message': str(e)}, status=500)



# ... existing code ...

class UserStatisticsView(APIView):
    """
    获取用户统计数据的接口
    返回：
    - vips: 会员总数
    - users: 用户总数
    - today_users: 今日新增用户数
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()

        try:
            from django.db.models import Sum
            total_revenue = Order.objects.filter(status=1).aggregate(total=Sum('actual_amount'))['total'] or 0
            # 查询会员总数
            vips = UserVIP.objects.filter(is_active=True).count()
            # 查询用户总数
            users = SysUser.objects.filter(isDelete=False, is_active=1,userRole="user").count()
            # 查询今日新增用户
            today_users = SysUser.objects.filter(
                isDelete=False,
                is_active=1,
                create_time__date=today
            ).count()

            data = {
                'vips': vips,
                'users': users,
                'total_revenue': total_revenue,
                'today_users': today_users,
            }

            return ResponseUtil.success(data=data)
        except Exception as e:
            return ResponseUtil.error(description=str(e))

# ... existing code ...



# 小程序的微信支付
# 读取配置文件
config = configparser.ConfigParser()
config.read('config/config.ini')

# 获取微信支付配置
appid = config.get('wechat_pay', 'appid')
mchid = config.get('wechat_pay', 'mchid')
PUBLIC_KEY_ID = config.get('wechat_pay', 'PUBLIC_KEY_ID')
apiv3_key = config.get('wechat_pay', 'api_key')
private_key_path = config.get('wechat_pay', 'private_key_path')
platform_cert_path = config.get('wechat_pay', 'platform_cert_path')  # 新增配置
pub_key_path = config.get('wechat_pay', 'pub_key_path')  # 新增配置
cert_serial_number = config.get('wechat_pay', 'cert_serial_number')
print(appid,mchid,apiv3_key,private_key_path,cert_serial_number)

# 加载私钥
with open(private_key_path, 'r') as f:
    private_key = f.read()
# print(private_key)
# 加载平台证书
with open(platform_cert_path, 'rb') as f:
    platform_cert = f.read()
# print(platform_cert)
with open(pub_key_path) as f:
    PUBLIC_KEY = f.read()
# print(PUBLIC_KEY)
# 初始化微信支付对象


# 回调解析数据
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
def decrypt(nonce, ciphertext, associated_data):
    key = apiv3_key
    key_bytes = str.encode(key)
    nonce_bytes = str.encode(nonce)
    ad_bytes = str.encode(associated_data)
    data = base64.b64decode(ciphertext)
    aesgcm = AESGCM(key_bytes)
    return aesgcm.decrypt(nonce_bytes, data, ad_bytes)


# 网页微信支付
class WeChatPayViewPC(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user

            # 获取商品 id
            product_id = request.data.get('product_id')
            if not product_id:
                return ResponseUtil.error(message='请提供商品 id')

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return ResponseUtil.error(message='商品不存在')

            description = product.description
            # 假设价格单位为分，需要根据实际情况调整
            amount = int(product.price * 100)  
            print(amount)
            print(cert_serial_number)

            wechat_pay = WeChatPay(
                wechatpay_type=WeChatPayType.NATIVE,
                mchid=mchid,
                private_key=private_key,
                cert_serial_no=cert_serial_number,
                appid=appid,
                apiv3_key=apiv3_key,
                cert_dir="./config/",
                public_key=PUBLIC_KEY,
                public_key_id=PUBLIC_KEY_ID,
            )

            out_trade_no = ''.join([str(random.randint(0, 9)) for _ in range(32)])
            # out_trade_no = str(uuid.uuid4()).replace('-', '')[:32]
            print(out_trade_no)
            print("-------------1-------------")


            # 调用微信支付统一下单接口
            now = datetime.now()
            ten_minutes_later = now + timedelta(minutes=10)
            time_expire = ten_minutes_later.strftime("%Y-%m-%dT%H:%M:%S+08:00")
            # print(wechat_pay.cert_serial_no)
            code, message  = wechat_pay.pay(
                description=description,
                time_expire=time_expire,
                out_trade_no=out_trade_no,
                notify_url='http://192.168.0.100/api/pay/wechat_pay_notify/',  # 支付结果通知地址
                amount={'total': amount},
                pay_type=WeChatPayType.NATIVE
            )

            print("-------------网页微信支付结果-------------")
            print(code,message)

            # 创建订单数据
            order = Order.objects.create(
                user=user,
                order_no=out_trade_no,
                total_amount=product.price,
                actual_amount=product.price,
                product=product,
                payment_method=2,  # 微信支付
                status=0,  # 待支付
                remark=description,
                create_time=timezone.now()
            )
            message = json.loads(message)
            message["orderid"] = out_trade_no

            return ResponseUtil.success(data=message)

        except Exception as e:
            logger.error(f"统一下单失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(message=f'统一下单失败: {str(e)}')

# 网页微信支付回调
class WeChatPayNotifyViewPC(APIView):
    # 微信支付回调不需要认证，移除认证和权限类
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        try:
            transaction_id = request.query_params.get('order_id')
            print(transaction_id)
            if not transaction_id:
                return ResponseUtil.error(message='缺少参数')
            wechat_pay = WeChatPay(
                wechatpay_type=WeChatPayType.NATIVE,
                mchid=mchid,
                private_key=private_key,
                cert_serial_no=cert_serial_number,
                appid=appid,
                apiv3_key=apiv3_key,
                cert_dir="./config/",
                public_key=PUBLIC_KEY,
                public_key_id=PUBLIC_KEY_ID
            )
            code, message = wechat_pay.query(
                out_trade_no=transaction_id
            )
            print('code: %s, message: %s' % (code, message))
            # order = Order.objects.get(order_no=transaction_id)
            message = json.loads(message)

            if code ==200 and message['trade_state'] == 'SUCCESS':

                # 获取商户订单号
                # out_trade_no = result['out_trade_no']
                try:
                    # 查询订单

                    order = Order.objects.get(order_no=transaction_id)
                    user = order.user
                    if order.status == 1:
                        return ResponseUtil.success(message='支付成功，用户积分已更新', data={
                        'order_no': transaction_id,
                        'new_points': user.points+user.vip_points
                    })
                    # 更新订单支付状态为已支付
                    order.status = 1  # 假设 1 表示已支付
                    order.save()

                    # 获取用户信息
                    if user:
                        # 获取订单关联产品的 points
                        product_points = order.product.points

                        # 检查商品的 method 字段是否为 vip1
                        if order.product.method == 'vip1':
                            start_time = timezone.now()
                            if UserVIP.objects.filter(user = user,is_active= 1).exists():
                                user_vip = UserVIP.objects.get(user = user)
                                user_vip.end_time = user_vip.end_time + relativedelta(months=1)
                                user_vip.save()
                            else:
                                end_time = start_time + relativedelta(months=1)
                                UserVIP.objects.create(
                                    user=user,
                                    start_time=start_time,
                                    end_time=end_time,
                                    level='vip_basic',
                                )
                            user.vip_points += product_points
                            user.save()
                        elif order.product.method == 'vip2':
                            start_time = timezone.now()
                            if UserVIP.objects.filter(user = user,is_active= 1).exists():
                                user_vip = UserVIP.objects.get(user = user)
                                user_vip.end_time = user_vip.end_time + relativedelta(months=6)
                                user_vip.save()
                            else:
                                end_time = start_time + relativedelta(months=6)
                                UserVIP.objects.create(
                                    user=user,
                                    start_time=start_time,
                                    end_time=end_time,
                                    level='vip_premium',
                                )
                            user.vip_points += product_points
                            user.save()
                        elif order.product.method == 'vip3':
                            start_time = timezone.now()
                            if UserVIP.objects.filter(user = user,is_active= 1).exists():
                                user_vip = UserVIP.objects.get(user = user)
                                user_vip.end_time = user_vip.end_time + relativedelta(months=12)
                                user_vip.save()
                            else:
                                end_time = start_time + relativedelta(months=12)
                                UserVIP.objects.create(
                                    user=user,
                                    start_time=start_time,
                                    end_time=end_time,
                                    level='vip_platinum',
                                )
                            user.vip_points += product_points
                            user.save()
                        else:
                            user.points += product_points
                            user.save()
                    else:
                        return ResponseUtil.error(message='用户不存在')

                    return ResponseUtil.success(message='支付成功，用户积分已更新', data={
                        'order_no': transaction_id,
                        'new_points': user.points+user.vip_points
                    })
                except Order.DoesNotExist:
                    return ResponseUtil.error(message='订单不存在')
            else:
                return ResponseUtil.success(message='尚未支付')

        except Exception as e:
            logger.error(f"处理微信支付回调失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(message=str(e))


# 小程序微信支付
class WeChatPayView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            # 从用户信息中获取 openid，假设用户模型中有 openid 字段
            openid = user.openid if hasattr(user, 'openid') else None
            if not openid:
                return ResponseUtil.error(message='用户未提供 openid')

            # 获取商品 id
            product_id = request.data.get('product_id')
            if not product_id:
                return ResponseUtil.error(message='请提供商品 id')

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return ResponseUtil.error(message='商品不存在')

            description = product.description
            # 假设价格单位为分，需要根据实际情况调整
            amount = int(product.price * 100)  
            print(amount)
            print(cert_serial_number)

            wechat_pay = WeChatPay(
                wechatpay_type=WeChatPayType.MINIPROG,
                mchid=mchid,
                private_key=private_key,
                cert_serial_no=cert_serial_number,
                appid=appid,
                apiv3_key=apiv3_key,
                cert_dir="./config/",
                public_key=PUBLIC_KEY,
                public_key_id=PUBLIC_KEY_ID,
                

                
            )


            # 生成唯一的订单号
            # out_trade_no = f"{uuid.uuid4()}"
            
            out_trade_no = ''.join([str(random.randint(0, 9)) for _ in range(32)])
            # out_trade_no = str(uuid.uuid4()).replace('-', '')[:32]
            print(out_trade_no)
            print("-------------1-------------")


            # 调用微信支付统一下单接口
            # print(wechat_pay.cert_serial_no)
            result = wechat_pay.pay(
                description=description,
                out_trade_no=out_trade_no,
                notify_url='https://www.qihuaimage.com/api/pay/wechat_pay_notify/',  # 支付结果通知地址
                amount={'total': amount},
                # amount=amount,
                payer={'openid': openid},
                # public_key_id= 'PUB_KEY_ID_0117120856372025042500321702000001',
                # public_key='0117120856372025042500321702000001'
            )

            print(result)


            if 'code' in result and result['code'] != 'SUCCESS':
                return ResponseUtil.error(data=result, message='统一下单失败')
            print("-------------2-------------")

            # 生成小程序端调起支付所需的参数
            # prepay_id = result['prepay_id']
            # 解析 JSON 字符串
            json_str = result[1]
            result_dict = json.loads(json_str)
            # 获取 prepay_id 的值
            prepay_id = result_dict.get('prepay_id')
            print(prepay_id)
            # 生成小程序端调起支付所需的参数
            # 正确生成小程序调起支付参数
            import secrets
            import string
            # 手动生成随机字符串
            characters = string.ascii_letters + string.digits
            nonce_str = ''.join(secrets.choice(characters) for _ in range(32))
            pay_params = {
                'appId': appid,
                'timeStamp': str(int(time.time())),
                'nonceStr': nonce_str,
                'package': f'prepay_id={prepay_id}',
                'signType': 'RSA',

            }
            # 生成签名
            sign_str = '\n'.join([
                pay_params['appId'],
                pay_params['timeStamp'],
                pay_params['nonceStr'],
                pay_params['package']
            ]) + '\n'
            sign_params_list = [
                pay_params['appId'],
                pay_params['timeStamp'],
                pay_params['nonceStr'],
                pay_params['package']
            ]
            print('-------------------')
            print(sign_params_list)
            pay_params['paySign'] = wechat_pay.sign(sign_params_list)
            print("-------------3-------------")


            # 创建订单数据
            order = Order.objects.create(
                user=user,
                order_no=out_trade_no,
                total_amount=product.price,
                actual_amount=product.price,
                product=product,
                payment_method=2,  # 微信支付
                status=0,  # 待支付
                remark=description,
                create_time=timezone.now()
            )
            pay_params["orderid"] = order.id

            return ResponseUtil.success(message='统一下单成功', data=pay_params)

        except Exception as e:
            logger.error(f"统一下单失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(message=f'统一下单失败: {str(e)}')

# 小程序微信支付回调
class WeChatPayNotifyView(APIView):
    # 微信支付回调不需要认证，移除认证和权限类
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            wechat_pay = WeChatPay(
                wechatpay_type=WeChatPayType.MINIPROG,
                mchid=mchid,
                private_key=private_key,
                cert_serial_no=cert_serial_number,
                appid=appid,
                apiv3_key=apiv3_key,
                cert_dir="./config/",
                public_key=PUBLIC_KEY,
                public_key_id=PUBLIC_KEY_ID
                
            )
            # 验证微信支付回调签名
            headers = request.headers
            body = request.data
            print(headers)
            print(body)
            result= decrypt(
                body['resource']['nonce'],
                body['resource']['ciphertext'],
                body['resource']['associated_data']
            )
            # result = base64.b64decode(body['resource']['ciphertext']).decode('utf-8')
            # result = wechat_pay.callback(headers, body)
            # 检查签名验证结果
            if not result:
                logger.error("微信支付回调签名验证失败")
                return ResponseUtil.error(message='签名验证失败')
            
            print("微信支付回调结果:", result)
            result = json.loads(result)
            if result['out_trade_no']:
                # 获取商户订单号
                out_trade_no = result['out_trade_no']
                try:
                    # 查询订单
                    order = Order.objects.get(order_no=out_trade_no)
                    # 更新订单支付状态为已支付
                    order.status = 1  # 假设 1 表示已支付
                    order.save()

                    # 获取用户信息
                    user = order.user
                    if user:
                        # 获取订单关联产品的 points
                        product_points = order.product.points

                        # 检查商品的 method 字段是否为 vip1
                        if order.product.method == 'vip1':
                            start_time = timezone.now()
                            if UserVIP.objects.filter(user = user,is_active= 1).exists():
                                user_vip = UserVIP.objects.get(user = user)
                                if order.product.way == 0:
                                    end_time = user_vip.end_time + relativedelta(days=1)
                                else:
                                    end_time = user_vip.end_time + relativedelta(months=1)
                                user_vip.end_time = end_time
                                user_vip.save()
                            else:
                                if order.product.way == 0:
                                    end_time = start_time + relativedelta(days=1)
                                else:
                                    end_time = start_time + relativedelta(months=1)
                                UserVIP.objects.create(
                                    user=user,
                                    start_time=start_time,
                                    end_time=end_time,
                                    level='vip_basic',
                                )
                            user.vip_points += product_points
                            user.save()
                        elif order.product.method == 'vip2':
                            start_time = timezone.now()
                            if UserVIP.objects.filter(user = user,is_active= 1).exists():
                                user_vip = UserVIP.objects.get(user = user)
                                user_vip.end_time = user_vip.end_time + relativedelta(months=3)
                                user_vip.save()
                            else:
                                end_time = start_time + relativedelta(months=3)
                                UserVIP.objects.create(
                                    user=user,
                                    start_time=start_time,
                                    end_time=end_time,
                                    level='vip_premium',
                                )
                            user.vip_points += product_points
                            user.save()
                        elif order.product.method == 'vip3':
                            start_time = timezone.now()
                            if UserVIP.objects.filter(user = user,is_active= 1).exists():
                                user_vip = UserVIP.objects.get(user = user)
                                user_vip.end_time = user_vip.end_time + relativedelta(months=12)
                                user_vip.save()
                            else:
                                end_time = start_time + relativedelta(months=12)
                                UserVIP.objects.create(
                                    user=user,
                                    start_time=start_time,
                                    end_time=end_time,
                                    level='vip_platinum',
                                )
                            user.vip_points += product_points
                            user.save()
                        else:
                            user.points += product_points
                            user.save()
                    else:
                        return ResponseUtil.error(message='用户不存在')

                    return ResponseUtil.success(message='支付成功，用户积分已更新', data={
                        'order_no': out_trade_no,
                        'new_points': user.points if user else None
                    })
                except Order.DoesNotExist:
                    return ResponseUtil.error(message='订单不存在')
            else:
                return ResponseUtil.error(message='无效的回调类型')

        except Exception as e:
            logger.error(f"处理微信支付回调失败: {str(e)}", exc_info=True)
            return ResponseUtil.error(message=str(e))

# 根据订单id获取订单信息
class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]  # 确保用户已认证

    def get(self, request):
        try:
            # 获取用户
            user = request.user
            order_id = request.GET.get('order_id')
            print(order_id)
            order_id = request.query_params.get('order_id')
            print(order_id)

            # 检查订单是否属于当前用户
            order = Order.objects.get(id=order_id, user=user)
            # 构建订单信息
            order_info = {
                'id': order.id,
                'total_amount': order.total_amount, 
                'actual_amount': order.actual_amount,
                'status': order.status,
            }
            return ResponseUtil.success(data=order_info)
        except Order.DoesNotExist:
            return ResponseUtil.error(message='订单不存在')





# 添加积分
class AddPointsView(APIView):
    permission_classes = [IsAuthenticated]  # 确保用户已认证

    def post(self, request):
        try:
            user = request.user  # 获取当前用户
            points = request.data.get('points')  # 获取要添加的积分

            if points is None:
                return ResponseUtil.error(message='请提供要添加的积分')

            # 检查积分是否为整数
            try:
                points = int(points)
            except ValueError:
                return ResponseUtil.error(message='积分必须为整数')

            # 更新用户的积分
            user.points += points
            user.save()

            return ResponseUtil.success(message='积分添加成功', data={'new_points': user.points})
        except Exception as e:
            return ResponseUtil.error(message=str(e))