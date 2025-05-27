from django.shortcuts import render
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from .models import (ChargingRequest, ChargingPile, ChargingSession, 
                    SystemParameter, Notification)
from .serialiazers import (ChargingRequestSerializer, ChargingRequestCreateSerializer,
                         ChargingPileSerializer, ChargingSessionSerializer,
                         SystemParameterSerializer, NotificationSerializer)
from .services import ChargingQueueService, BillingService

# Create your views here.

class ChargingRequestView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """提交充电请求"""
        serializer = ChargingRequestCreateSerializer(data=request.data)
        if serializer.is_valid():
            # 检查用户是否已有未完成的请求
            existing_request = ChargingRequest.objects.filter(
                user=request.user,
                current_status__in=['waiting', 'charging']
            ).first()
            
            if existing_request:
                return Response({
                    'success': False,
                    'error': {
                        'code': 'DUPLICATE_REQUEST',
                        'message': '您已有未完成的充电请求'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 检查等候区容量
            queue_service = ChargingQueueService()
            if not queue_service.can_join_queue():
                return Response({
                    'success': False,
                    'error': {
                        'code': 'QUEUE_FULL',
                        'message': '等候区已满，请稍后再试'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                charging_request = serializer.save(user=request.user)
                queue_service.add_to_queue(charging_request)
            
            response_data = ChargingRequestSerializer(charging_request).data
            return Response({
                'success': True,
                'message': '充电请求提交成功',
                'data': {
                    'queue_number': response_data['queue_number'],
                    'charging_mode': response_data['charging_mode'],
                    'requested_amount': response_data['requested_amount'],
                    'estimated_wait_time': response_data['estimated_wait_time'],
                    'queue_position': response_data['queue_position']
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': '参数验证失败',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def modify_charging_request(request, request_id):
    """修改充电请求"""
    charging_request = get_object_or_404(
        ChargingRequest, 
        id=request_id, 
        user=request.user,
        current_status='waiting'
    )
    
    serializer = ChargingRequestCreateSerializer(
        charging_request, 
        data=request.data, 
        partial=True
    )
    
    if serializer.is_valid():
        with transaction.atomic():
            charging_request = serializer.save()
            # 重新计算排队位置
            queue_service = ChargingQueueService()
            queue_service.update_queue_position(charging_request)
        
        return Response({
            'success': True,
            'message': '充电请求修改成功',
            'data': {
                'queue_number': charging_request.queue_number,
                'new_position': charging_request.queue_position,
                'estimated_wait_time': charging_request.estimated_wait_time
            }
        })
    
    return Response({
        'success': False,
        'error': {
            'code': 'VALIDATION_ERROR',
            'message': '参数验证失败',
            'details': serializer.errors
        }
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancel_charging_request(request, request_id):
    """取消充电请求"""
    charging_request = get_object_or_404(
        ChargingRequest,
        id=request_id,
        user=request.user,
        current_status__in=['waiting', 'charging']
    )
    
    if charging_request.current_status == 'charging':
        return Response({
            'success': False,
            'error': {
                'code': 'INVALID_REQUEST',
                'message': '正在充电中，无法取消请求'
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    with transaction.atomic():
        charging_request.current_status = 'cancelled'
        charging_request.save()
        
        # 更新后续排队位置
        queue_service = ChargingQueueService()
        queue_service.remove_from_queue(charging_request)
    
    return Response({
        'success': True,
        'message': '充电请求已取消'
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def charging_request_status(request):
    """查看当前充电请求状态"""
    charging_request = ChargingRequest.objects.filter(
        user=request.user,
        current_status__in=['waiting', 'charging']
    ).first()
    
    if not charging_request:
        return Response({
            'success': False,
            'error': {
                'code': 'RESOURCE_NOT_FOUND',
                'message': '没有找到活跃的充电请求'
            }
        }, status=status.HTTP_404_NOT_FOUND)
    
    # 计算前面等待的数量
    ahead_count = ChargingRequest.objects.filter(
        charging_mode=charging_request.charging_mode,
        current_status='waiting',
        queue_position__lt=charging_request.queue_position
    ).count()
    
    data = ChargingRequestSerializer(charging_request).data
    data['ahead_count'] = ahead_count
    
    return Response({
        'success': True,
        'data': data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_charging(request):
    """结束充电"""
    charging_request = get_object_or_404(
        ChargingRequest,
        user=request.user,
        current_status='charging'
    )
    
    with transaction.atomic():
        # 结束充电会话
        session = charging_request.session
        session.end_time = timezone.now()
        
        # 计算费用
        billing_service = BillingService()
        billing_service.calculate_bill(session)
        session.save()
        
        # 更新请求状态
        charging_request.current_status = 'completed'
        charging_request.end_time = timezone.now()
        charging_request.save()
        
        # 释放充电桩
        pile = charging_request.charging_pile
        pile.is_working = False
        pile.save()
        
        # 处理下一个排队请求
        queue_service = ChargingQueueService()
        queue_service.process_next_in_queue(pile)
    
    return Response({
        'success': True,
        'message': '充电已结束',
        'data': {
            'bill_id': str(session.id),
            'total_amount': session.charging_amount,
            'total_cost': float(session.total_cost),
            'charging_duration': session.charging_duration
        }
    })

@api_view(['GET'])
def queue_status(request):
    """查看排队状态"""
    fast_waiting = ChargingRequest.objects.filter(
        charging_mode='fast',
        current_status='waiting'
    ).order_by('queue_position')
    
    slow_waiting = ChargingRequest.objects.filter(
        charging_mode='slow', 
        current_status='waiting'
    ).order_by('queue_position')
    
    # 获取等候区容量配置
    try:
        waiting_area_size = SystemParameter.objects.get(
            param_key='WaitingAreaSize'
        ).get_value()
    except SystemParameter.DoesNotExist:
        waiting_area_size = 10  # 默认值
    
    current_waiting = ChargingRequest.objects.filter(
        current_status='waiting'
    ).count()
    
    return Response({
        'success': True,
        'data': {
            'fast_charging': {
                'waiting_count': fast_waiting.count(),
                'queue_list': [
                    {
                        'queue_number': req.queue_number,
                        'estimated_wait_time': req.estimated_wait_time
                    }
                    for req in fast_waiting[:5]  # 显示前5个
                ]
            },
            'slow_charging': {
                'waiting_count': slow_waiting.count(),
                'queue_list': [
                    {
                        'queue_number': req.queue_number,
                        'estimated_wait_time': req.estimated_wait_time
                    }
                    for req in slow_waiting[:5]  # 显示前5个
                ]
            },
            'waiting_area_capacity': {
                'current': current_waiting,
                'max': waiting_area_size
            }
        }
    })

@api_view(['GET'])
def piles_status(request):
    """查看充电桩状态"""
    fast_piles = ChargingPile.objects.filter(pile_type='fast')
    slow_piles = ChargingPile.objects.filter(pile_type='slow')
    
    fast_data = ChargingPileSerializer(fast_piles, many=True).data
    slow_data = ChargingPileSerializer(slow_piles, many=True).data
    
    return Response({
        'success': True,
        'data': {
            'fast_piles': fast_data,
            'slow_piles': slow_data
        }
    })

# 账单相关视图
class BillListView(generics.ListAPIView):
    serializer_class = ChargingSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = ChargingSession.objects.filter(user=self.request.user)
        
        # 日期过滤
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(start_time__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__date__lte=end_date)
            
        return queryset.order_by('-start_time')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'success': True,
                'data': {
                    'bills': serializer.data,
                    'pagination': {
                        'current_page': self.paginator.page.number,
                        'total_pages': self.paginator.page.paginator.num_pages,
                        'total_count': queryset.count()
                    }
                }
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': {
                'bills': serializer.data,
                'pagination': {
                    'current_page': 1,
                    'total_pages': 1,
                    'total_count': queryset.count()
                }
            }
        })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bill_detail(request, bill_id):
    """查看单个详单"""
    session = get_object_or_404(ChargingSession, id=bill_id, user=request.user)
    
    return Response({
        'success': True,
        'data': {
            'bill_id': str(session.id),
            'generated_time': session.created_at,
            'pile_id': session.pile.pile_id,
            'charging_amount': session.charging_amount,
            'charging_duration': session.charging_duration,
            'start_time': session.start_time,
            'end_time': session.end_time,
            'cost_breakdown': {
                'peak_cost': float(session.peak_cost),
                'normal_cost': float(session.normal_cost),
                'valley_cost': float(session.valley_cost),
                'service_cost': float(session.service_cost),
                'total_cost': float(session.total_cost)
            },
            'time_breakdown': {
                'peak_hours': session.peak_hours,
                'normal_hours': session.normal_hours,
                'valley_hours': session.valley_hours
            }
        }
    })

# 通知相关视图
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications(request):
    """获取用户通知"""
    notifications = Notification.objects.filter(user=request.user)[:20]
    serializer = NotificationSerializer(notifications, many=True)
    
    return Response({
        'success': True,
        'data': serializer.data
    })

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """标记通知已读"""
    notification = get_object_or_404(
        Notification, 
        id=notification_id, 
        user=request.user
    )
    
    notification.read = True
    notification.save()
    
    return Response({
        'success': True,
        'message': '通知已标记为已读'
    })

@api_view(['GET'])
def system_parameters(request):
    """获取系统参数（公开接口）"""
    try:
        # 获取四个核心参数
        fast_pile_num = SystemParameter.objects.get(param_key='FastChargingPileNum').get_value()
        slow_pile_num = SystemParameter.objects.get(param_key='TrickleChargingPileNum').get_value()
        waiting_area_size = SystemParameter.objects.get(param_key='WaitingAreaSize').get_value()
        queue_length = SystemParameter.objects.get(param_key='ChargingQueueLen').get_value()
        
        # 获取费率参数
        peak_rate = SystemParameter.objects.get(param_key='peak_rate').get_value()
        normal_rate = SystemParameter.objects.get(param_key='normal_rate').get_value()
        valley_rate = SystemParameter.objects.get(param_key='valley_rate').get_value()
        service_rate = SystemParameter.objects.get(param_key='service_rate').get_value()
        
        return Response({
            'success': True,
            'data': {
                'FastChargingPileNum': fast_pile_num,
                'TrickleChargingPileNum': slow_pile_num,
                'WaitingAreaSize': waiting_area_size,
                'ChargingQueueLen': queue_length,
                'pricing': {
                    'peak_rate': peak_rate,
                    'normal_rate': normal_rate,
                    'valley_rate': valley_rate,
                    'service_rate': service_rate
                },
                'time_periods': {
                    'peak': ['10:00-15:00', '18:00-21:00'],
                    'normal': ['07:00-10:00', '15:00-18:00', '21:00-23:00'],
                    'valley': ['23:00-07:00']
                }
            }
        })
    except SystemParameter.DoesNotExist as e:
        return Response({
            'success': False,
            'error': {
                'code': 'PARAMETER_NOT_FOUND',
                'message': f'系统参数未找到: {str(e)}'
            }
        }, status=status.HTTP_404_NOT_FOUND)
