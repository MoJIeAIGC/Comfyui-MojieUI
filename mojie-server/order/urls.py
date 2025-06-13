from django.urls import path
from order.views import (
    OrderView, OrderDetailView,
    PaymentView, PaymentDetailView, PaymentNotificationView,
    RefundView, RefundDetailView,
    TestOrderView, TestPaymentFlowView,
    AlipayReturnView, getOrder, getProduct, UpdateProductView,
    AliPayView, WeChatPayView,
    ProductPaymentView, ProductDeleteView, AddPointsView,userProduct,
    TestPaymentSuccessView, WeChatAuthView, daily_revenue_last_seven_days, WeChatPayViewPC, WeChatPayNotifyView,
    WeChatPayNotifyViewPC, TestManualNotificationView,UserStatisticsView
)

urlpatterns = [
    # 订单相关
    path('orders/', OrderView.as_view(), name='order-list'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    
    # 支付相关
    path('payments/', PaymentView.as_view(), name='payment-list'),
    path('payments/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),

    # 统一支付通知处理（支持多种支付方式）
    path('payments/notification/<str:payment_method>/', PaymentNotificationView.as_view(), name='payment-notification'),
    
    # 退款相关
    path('refunds/', RefundView.as_view(), name='refund-list'),
    path('refunds/<int:pk>/', RefundDetailView.as_view(), name='refund-detail'),
    
    # 支付宝相关
    path('alipay/', AliPayView.as_view(), name='alipay-pay'),
    path('alipay/return/', AlipayReturnView.as_view(), name='alipay-return'),

    # 微信相关
    path('pay/weixin/openid/', WeChatAuthView.as_view(), name='weixin-openid'),
    
    # 测试相关
    path('test/test_payment_flow/', TestPaymentFlowView.as_view(), name='test_payment_flow'),
    path('test/manual_notification/', TestManualNotificationView.as_view(), name='test_manual_notification'),

    # 后台管理相关
    path('mojie/order_list/', getOrder.as_view(), name='test-payment-flow'),
    path('mojie/product_list/', getProduct.as_view(), name='test-payment-flow'),
    path('mojie/money_list/', daily_revenue_last_seven_days.as_view(), name='后台营业额数据'),
    path('mojie/product/<int:pk>/', UpdateProductView.as_view(), name='test-payment-flow'),
    path('product/<int:pk>/', ProductDeleteView.as_view(), name='example-soft-delete'),
    path('usercount/', UserStatisticsView.as_view(), name='example-soft-delete'),

    # 商品查询
    path('getpro/', userProduct.as_view(), name='test-payment-flow'),



    # 商品支付
    path('product/payment/', ProductPaymentView.as_view(), name='product-payment'),
    path('test-payment-success/', TestPaymentSuccessView.as_view(), name='test-payment-success'),

    # 小程序微信支付
    path('wechat_pay/', WeChatPayView.as_view(), name='wechat_pay'),
    path('wechat_pay_notify/', WeChatPayNotifyView.as_view(), name='wechat_pay_notify'),
    path('getorder/', OrderDetailView.as_view(), name='wechat_pay_notify'),

    # 网页微信支付
    path('wechat_pay_pc/', WeChatPayViewPC.as_view(), name='wechat_pay'),
    path('getorder_pc/', WeChatPayNotifyViewPC.as_view(), name='wechat_pay_notify'),

    path('addpoint/', AddPointsView.as_view(), name='wechat_pay'),

]