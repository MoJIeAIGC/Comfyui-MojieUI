from rest_framework import serializers
from .models import Order, Payment, Refund,Product
from user.serializers import UserSerializer

class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    class Meta:
        model = Order
        fields = [
            'id', 'order_no', 'user', 'total_amount', 'actual_amount',
            'status', 'status_display', 'payment_method', 'payment_method_display',
            'create_time', 'update_time', 'pay_time', 'description'
        ]
        read_only_fields = [
            'id', 'order_no', 'user', 'status', 'create_time', 'update_time',
            'pay_time', 'payment_method'
        ]

class PaymentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    order = serializers.PrimaryKeyRelatedField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'order', 'amount', 'currency', 'status', 'status_display',
            'payment_method', 'payment_method_display', 'create_time', 'update_time',
            'pay_time', 'description', 'transaction_id'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'create_time', 'update_time', 
            'pay_time', 'transaction_id'
        ]

class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['order', 'amount', 'currency', 'payment_method', 'description']
    
    def validate(self, data):
        order = data['order']
        if order.status != 0:  # 待支付
            raise serializers.ValidationError("只有待支付订单可以创建支付")
        if float(data['amount']) != float(order.actual_amount):
            raise serializers.ValidationError("支付金额必须等于订单实付金额")
        return data

class RefundSerializer(serializers.ModelSerializer):
    payment = PaymentSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'payment', 'amount', 'reason', 'status', 'status_display',
            'create_time', 'update_time', 'refund_time', 'transaction_id'
        ]
        read_only_fields = [
            'id', 'status', 'create_time', 'update_time',
            'refund_time', 'transaction_id'
        ]

class RefundCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = ['payment', 'amount', 'reason']
    
    def validate(self, data):
        payment = data['payment']
        if payment.status != 1:  # 已支付
            raise serializers.ValidationError("只有已支付的订单才能退款")
        if float(data['amount']) > float(payment.amount):
            raise serializers.ValidationError("退款金额不能大于支付金额")
        return data

class PaymentNotificationSerializer(serializers.Serializer):
    order_id = serializers.CharField(max_length=100)
    transaction_id = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
    signature = serializers.CharField(max_length=256) 


class ProductSerializer(serializers.ModelSerializer):
    """
    用于序列化和反序列化 Product 模型的序列化器。

    这个序列化器将 Product 模型的字段映射到 JSON 数据，以便在 API 中进行传输。
    它支持创建和更新 Product 实例。
    """
    class Meta:
        model = Product
        fields = [
            'id','price',  'points' ,'description','method','way','gift_points','about'
        ]
        # read_only_fields = [
        #     'id', 'created_at', 'updated_at'
        # ]