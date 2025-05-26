# backend/charging/views/admin_views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from charging.utils.config_manager import ConfigManager

@api_view(['GET'])
def get_system_parameters(request):
    """获取系统参数"""
    parameters = ConfigManager.get_all_parameters()
    return Response({
        'success': True,
        'data': parameters
    })

@api_view(['PUT'])
@permission_classes([IsAdminUser])
def update_system_parameters(request):
    """更新系统参数"""
    data = request.data
    
    # 验证参数
    allowed_params = ['FastChargingPileNum', 'TrickleChargingPileNum', 'WaitingAreaSize', 'ChargingQueueLen']
    
    updated_params = {}
    for key, value in data.items():
        if key in allowed_params:
            if ConfigManager.set_parameter(key, value, 'int'):
                updated_params[key] = value
    
    return Response({
        'success': True,
        'message': '系统参数更新成功',
        'data': updated_params
    })