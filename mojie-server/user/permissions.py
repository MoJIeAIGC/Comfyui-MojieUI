from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    自定义权限类：
    - 对象的所有者可以编辑
    - 其他用户只能查看
    """
    
    def has_object_permission(self, request, view, obj):
        # 如果是只读操作（GET, HEAD, OPTIONS），允许所有用户访问
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # 如果是写操作，检查用户是否是对象的所有者
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'payment') and hasattr(obj.payment, 'user'):
            return obj.payment.user == request.user
        elif hasattr(obj, 'order') and hasattr(obj.order, 'user'):
            return obj.order.user == request.user
            
        return False 