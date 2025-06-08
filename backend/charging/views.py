from django.shortcuts import render
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from .models import (ChargingRequest, ChargingPile, ChargingSession, 
                    SystemParameter, Notification)
from .serialiazers import (ChargingRequestSerializer, ChargingRequestCreateSerializer,
                         ChargingPileSerializer, ChargingSessionSerializer,
                         SystemParameterSerializer, NotificationSerializer)
from .services import AdvancedChargingQueueService, BillingService
from charging.utils.parameter_manager import ParameterManager

# Create your views here.

class ChargingRequestView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """提交充电请求"""
        serializer = ChargingRequestCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # 车辆验证已在序列化器中完成
            
            # 检查外部等候区容量
            queue_service = AdvancedChargingQueueService()
            if not queue_service.can_join_external_queue():
                return Response({
                    'success': False,
                    'error': {
                        'code': 'EXTERNAL_QUEUE_FULL',
                        'message': '外部等候区已满，请稍后再试'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                charging_request = serializer.save(user=request.user)
                queue_service.add_to_external_queue(charging_request)
            
            response_data = ChargingRequestSerializer(charging_request).data
            
            return Response({
                'success': True,
                'message': '充电请求提交成功',
                'data': response_data
            })
        
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
    
    # 只有在外部等候区的请求才能修改
    if charging_request.queue_level not in ['external_waiting']:
        return Response({
            'success': False,
            'error': {
                'code': 'INVALID_REQUEST',
                'message': '只有在外部等候区的请求才能修改'
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = ChargingRequestCreateSerializer(
        charging_request, 
        data=request.data, 
        partial=True
    )
    
    if serializer.is_valid():
        with transaction.atomic():
            old_mode = charging_request.charging_mode
            charging_request = serializer.save()
            
            # 如果充电模式改变，需要重新计算等待时间
            if old_mode != charging_request.charging_mode:
                queue_service = AdvancedChargingQueueService()
                charging_request.estimated_wait_time = queue_service._calculate_external_wait_time(charging_request)
                charging_request.save()
        
        return Response({
            'success': True,
            'message': '充电请求修改成功',
            'data': {
                'queue_number': charging_request.queue_number,
                'queue_status': charging_request.get_queue_status_display(),
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
        queue_service = AdvancedChargingQueueService()
        queue_service.cancel_charging_request(charging_request)
    
    return Response({
        'success': True,
        'message': '充电请求已取消'
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_charging_mode(request, request_id):
    """修改充电类型（仅限外部等候区的请求）"""
    try:
        charging_request = get_object_or_404(
            ChargingRequest,
            id=request_id,
            user=request.user
        )
        
        new_charging_mode = request.data.get('charging_mode')
        if not new_charging_mode:
            return Response({
                'success': False,
                'error': {
                    'code': 'MISSING_PARAMETER',
                    'message': '缺少充电类型参数'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if new_charging_mode not in ['fast', 'slow']:
            return Response({
                'success': False,
                'error': {
                    'code': 'INVALID_PARAMETER',
                    'message': '充电类型必须是 fast 或 slow'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 使用队列服务修改充电类型
        queue_service = AdvancedChargingQueueService()
        updated_request = queue_service.change_charging_mode(charging_request, new_charging_mode)
        
        # 返回更新后的请求信息
        serializer = ChargingRequestSerializer(updated_request)
        
        return Response({
            'success': True,
            'message': '充电类型修改成功',
            'data': serializer.data
        })
        
    except ValueError as e:
        return Response({
            'success': False,
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': str(e)
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': f'修改充电类型失败: {str(e)}'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def charging_request_status(request):
    """查看当前充电请求状态"""
    try:
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
            }, status=status.HTTP_200_OK)
        
        # 根据队列层级计算前面等待的数量
        ahead_count = 0
        if charging_request.queue_level == 'external_waiting':
            ahead_count = charging_request.external_queue_position - 1
        elif charging_request.queue_level == 'pile_queue':
            ahead_count = charging_request.pile_queue_position - 1
        
        data = ChargingRequestSerializer(charging_request).data
        data['ahead_count'] = ahead_count
        data['queue_status'] = charging_request.get_queue_status_display()
        
        return Response({
            'success': True,
            'data': data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': f'查询充电状态失败: {str(e)}'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def public_system_status(request):
    """公开的系统状态接口，不需要认证"""
    try:
        # 获取基本系统统计
        total_piles = ChargingPile.objects.count()
        working_piles = ChargingPile.objects.filter(is_working=True).count()
        waiting_requests = ChargingRequest.objects.filter(current_status='waiting').count()
        charging_requests = ChargingRequest.objects.filter(current_status='charging').count()
        
        return Response({
            'success': True,
            'data': {
                'system_status': 'online',
                'total_piles': total_piles,
                'available_piles': total_piles - working_piles,
                'working_piles': working_piles,
                'waiting_count': waiting_requests,
                'charging_count': charging_requests
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': {
                'code': 'SYSTEM_ERROR',
                'message': '系统状态查询失败'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_charging(request):
    """结束充电"""
    # 获取要结束的充电请求ID
    request_id = request.data.get('request_id')
    
    if request_id:
        # 通过请求ID查找
        charging_request = get_object_or_404(
            ChargingRequest,
            id=request_id,
            user=request.user,
            current_status='charging'
        )
    else:
        # 向后兼容：查找用户的充电请求
        charging_request = get_object_or_404(
            ChargingRequest,
            user=request.user,
            current_status='charging'
        )
    
    try:
        with transaction.atomic():
            # 计算账单
            session = charging_request.session
            billing_service = BillingService()
            billing_service.calculate_bill(session)
            session.save()
            
            # 完成充电
            charging_request.current_amount = charging_request.requested_amount
            charging_request.current_status = 'completed'
            charging_request.end_time = timezone.now()
            charging_request.save()
            
            # 处理后续逻辑
            if hasattr(charging_request, 'session'):
                session = charging_request.session
                session.end_time = timezone.now()
                session.charging_amount = charging_request.requested_amount
                
                billing_service = BillingService()
                billing_service.calculate_bill(session)
                session.save()
            
            # 使用新的队列服务完成充电
            queue_service = AdvancedChargingQueueService()
            queue_service.complete_charging(charging_request)
            
            # 发送完成通知
            Notification.objects.create(
                user=charging_request.user,
                type='charging_complete',
                message=f'您的充电请求 {charging_request.queue_number} 已完成，总费用：{session.total_cost}元'
            )
        
        return Response({
            'success': True,
            'message': '充电已结束',
            'data': {
                'session_id': str(session.id),
                'total_amount': session.charging_amount,
                'total_cost': float(session.total_cost),
                'charging_duration': session.charging_duration
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': f'结束充电失败: {str(e)}'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def update_charging_progress(request):
    """手动更新充电进度API - 仅管理员可用"""
    action = request.data.get('action', 'auto')
    amount = request.data.get('amount', 0)
    user_id = request.data.get('user_id')  # 管理员可以指定用户ID
    request_id = request.data.get('request_id')  # 或者直接指定请求ID
    
    # 获取指定的充电请求
    if request_id:
        charging_request = ChargingRequest.objects.filter(
            id=request_id,
            current_status='charging'
        ).first()
    elif user_id:
        charging_request = ChargingRequest.objects.filter(
            user_id=user_id,
            current_status='charging'
        ).first()
    else:
        return Response({
            'success': False,
            'error': {
                'code': 'MISSING_PARAMETER',
                'message': '必须提供request_id或user_id参数'
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not charging_request:
        return Response({
            'success': False,
            'error': {
                'code': 'NO_CHARGING_REQUEST',
                'message': '没有找到正在充电的请求'
            }
        }, status=status.HTTP_404_NOT_FOUND)
    
    try:
        with transaction.atomic():
            old_amount = charging_request.current_amount
            
            if action == 'auto':
                # 自动计算进度
                from .management.commands.update_charging_progress import Command
                cmd = Command()
                cmd.update_request_progress(charging_request)
                
            elif action == 'increase':
                # 增加指定量
                new_amount = min(
                    charging_request.current_amount + amount,
                    charging_request.requested_amount
                )
                charging_request.current_amount = new_amount
                charging_request.save()
                
            elif action == 'decrease':
                # 减少指定量
                new_amount = max(
                    charging_request.current_amount - amount,
                    0
                )
                charging_request.current_amount = new_amount
                charging_request.save()
                
            elif action == 'set_percentage':
                # 设置到指定百分比
                percentage = min(max(amount, 0), 100) / 100
                new_amount = charging_request.requested_amount * percentage
                charging_request.current_amount = new_amount
                charging_request.save()
                
            elif action == 'complete':
                # 使用新的队列服务完成充电
                queue_service = AdvancedChargingQueueService()
                queue_service.complete_charging(charging_request)
                
                return Response({
                    'success': True,
                    'message': f'充电请求 {charging_request.queue_number} 已完成',
                    'data': {
                        'old_amount': old_amount,
                        'new_amount': charging_request.current_amount,
                        'progress_percentage': 100.0,
                        'status': 'completed',
                        'user': charging_request.user.username
                    }
                })
            
            # 更新会话数据
            if hasattr(charging_request, 'session'):
                session = charging_request.session
                session.charging_amount = charging_request.current_amount
                session.save()
            
            progress_percentage = (charging_request.current_amount / charging_request.requested_amount) * 100
            
            return Response({
                'success': True,
                'message': f'用户 {charging_request.user.username} 的充电进度已更新：{old_amount:.2f} -> {charging_request.current_amount:.2f} kWh',
                'data': {
                    'old_amount': old_amount,
                    'new_amount': charging_request.current_amount,
                    'progress_percentage': progress_percentage,
                    'remaining_amount': charging_request.requested_amount - charging_request.current_amount,
                    'status': charging_request.current_status,
                    'user': charging_request.user.username,
                    'queue_number': charging_request.queue_number
                }
            })
            
    except Exception as e:
        return Response({
            'success': False,
            'error': {
                'code': 'UPDATE_ERROR',
                'message': f'更新充电进度失败：{str(e)}'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def enhanced_queue_status(request):
    """获取增强的排队状态（支持多级队列）"""
    try:
        queue_service = AdvancedChargingQueueService()
        queue_data = queue_service.get_enhanced_queue_status()
        
        return Response({
            'success': True,
            'data': queue_data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': f'查询排队状态失败: {str(e)}'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def queue_status(request):
    """获取排队状态（保持向后兼容）"""
    try:
        # 使用增强的队列服务
        queue_service = AdvancedChargingQueueService()
        enhanced_data = queue_service.get_queue_status()
        
        # 转换为旧格式以保持兼容性
        fast_data = enhanced_data.get('fast', {})
        slow_data = enhanced_data.get('slow', {})
        
        # 等候区容量 - 使用新的参数管理器
        waiting_area_max = ParameterManager.get_parameter('external_waiting_area_size', 50)
        
        # 计算总等待人数
        total_waiting = fast_data.get('total_waiting', 0) + slow_data.get('total_waiting', 0)
        
        return Response({
            'success': True,
            'data': {
                'fast_charging': {
                    'waiting_count': fast_data.get('total_waiting', 0),
                    'queue_list': fast_data.get('external_waiting', {}).get('queue_list', [])
                },
                'slow_charging': {
                    'waiting_count': slow_data.get('total_waiting', 0),
                    'queue_list': slow_data.get('external_waiting', {}).get('queue_list', [])
                },
                'waiting_area_capacity': {
                    'current': total_waiting,
                    'max': waiting_area_max
                }
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': f'查询排队状态失败: {str(e)}'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def piles_status(request):
    """获取充电桩状态"""
    fast_piles = ChargingPile.objects.filter(pile_type='fast')
    slow_piles = ChargingPile.objects.filter(pile_type='slow')
    
    def get_pile_data(pile):
        current_user = None
        if pile.is_working:
            current_request = ChargingRequest.objects.filter(
                charging_pile=pile,
                current_status='charging'
            ).first()
            if current_request:
                current_user = current_request.user.username
        
        return {
            'pile_id': pile.pile_id,
            'status': pile.status,
            'is_working': pile.is_working,
            'current_user': current_user
        }
    
    return Response({
        'success': True,
        'data': {
            'fast_piles': [get_pile_data(pile) for pile in fast_piles],
            'slow_piles': [get_pile_data(pile) for pile in slow_piles]
        }
    })

@api_view(['GET'])
def system_parameters(request):
    """获取系统参数"""
    try:
        # 获取定价参数
        pricing_params = {
            'peak_rate': SystemParameter.objects.get(param_key='peak_rate').get_value(),
            'normal_rate': SystemParameter.objects.get(param_key='normal_rate').get_value(), 
            'valley_rate': SystemParameter.objects.get(param_key='valley_rate').get_value(),
            'service_rate': SystemParameter.objects.get(param_key='service_rate').get_value(),
        }
        
        # 获取容量参数
        capacity_params = {
            'fast_pile_count': SystemParameter.objects.get(param_key='FastChargingPileNum').get_value(),
            'slow_pile_count': SystemParameter.objects.get(param_key='TrickleChargingPileNum').get_value(),
            'waiting_area_size': SystemParameter.objects.get(param_key='WaitingAreaSize').get_value(),
        }
        
        # 获取充电功率参数
        charging_power_params = {
            'fast_charging_power': SystemParameter.objects.get(param_key='fast_charging_power').get_value(),
            'slow_charging_power': SystemParameter.objects.get(param_key='slow_charging_power').get_value(),
        }
        
        return Response({
            'success': True,
            'data': {
                'pricing': pricing_params,
                'capacity': capacity_params,
                'charging_power': charging_power_params
            }
        })
        
    except SystemParameter.DoesNotExist as e:
        return Response({
            'success': False,
            'error': {
                'code': 'MISSING_PARAMETER',
                'message': f'系统参数不存在: {str(e)}'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

class ChargingHistoryView(generics.ListAPIView):
    """用户充电历史记录视图 - 基于充电请求"""
    serializer_class = ChargingRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # 基于ChargingRequest而不是ChargingSession
        queryset = ChargingRequest.objects.filter(
            user=self.request.user,
            current_status__in=['completed', 'cancelled']  # 只显示已完成或已取消的请求
        ).select_related('charging_pile', 'vehicle', 'session')
        
        # 多种筛选条件
        pile_type = self.request.query_params.get('pile_type')  # fast/slow
        pile_id = self.request.query_params.get('pile_id')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        min_amount = self.request.query_params.get('min_amount')
        max_amount = self.request.query_params.get('max_amount')
        min_cost = self.request.query_params.get('min_cost')
        max_cost = self.request.query_params.get('max_cost')
        
        # 筛选条件
        if pile_type and pile_type != 'all':
            queryset = queryset.filter(charging_mode=pile_type)
        if pile_id:
            queryset = queryset.filter(charging_pile__pile_id=pile_id)
        if start_date:
            queryset = queryset.filter(start_time__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__date__lte=end_date)
        if min_amount:
            queryset = queryset.filter(current_amount__gte=float(min_amount))
        if max_amount:
            queryset = queryset.filter(current_amount__lte=float(max_amount))
        if min_cost:
            queryset = queryset.filter(session__total_cost__gte=float(min_cost))
        if max_cost:
            queryset = queryset.filter(session__total_cost__lte=float(max_cost))
            
        # 排序 - 调整字段名以匹配ChargingRequest
        order_by = self.request.query_params.get('order_by', '-created_at')
        valid_order_fields = [
            'start_time', '-start_time', 'current_amount', '-current_amount', 
            'created_at', '-created_at', 'updated_at', '-updated_at',
            'session__total_cost', '-session__total_cost'
        ]
        if order_by in valid_order_fields:
            queryset = queryset.order_by(order_by)
        else:
            queryset = queryset.order_by('-created_at')
            
        return queryset
    
    def list(self, request, *args, **kwargs):
        # 使用Django REST framework的标准分页机制
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def charging_statistics(request):
    """用户充电统计分析 - 基于充电请求"""
    user = request.user
    
    # 时间范围参数
    days = int(request.GET.get('days', 30))  # 默认30天
    start_date = timezone.now() - timezone.timedelta(days=days)
    
    # 基础查询 - 使用ChargingRequest
    requests = ChargingRequest.objects.filter(
        user=user,
        current_status='completed',  # 只统计已完成的请求
        end_time__gte=start_date
    ).select_related('session')
    
    # 基础统计
    total_requests = requests.count()
    if total_requests == 0:
        return Response({
            'success': True,
            'data': {
                'period_days': days,
                'total_requests': 0,
                'statistics': None
            }
        })
    
    from django.db.models import Sum, Avg, Count, Max, Min
    from decimal import Decimal
    
    # 聚合统计
    aggregates = requests.aggregate(
        total_amount=Sum('current_amount'),
        avg_amount=Avg('current_amount'),
        max_amount=Max('current_amount'),
        min_amount=Min('current_amount'),
    )
    
    # 费用统计（需要通过session）
    cost_stats = requests.filter(session__isnull=False).aggregate(
        total_cost=Sum('session__total_cost'),
        avg_cost=Avg('session__total_cost'),
        max_cost=Max('session__total_cost'),
        min_cost=Min('session__total_cost'),
        total_duration=Sum('session__charging_duration'),
        avg_duration=Avg('session__charging_duration')
    )
    
    # 合并统计结果
    aggregates.update(cost_stats)
    
    # 按充电模式统计
    mode_stats = requests.values('charging_mode').annotate(
        count=Count('id'),
        total_amount=Sum('current_amount'),
        avg_amount=Avg('current_amount'),
    ).order_by('charging_mode')
    
    # 为模式统计添加费用信息
    mode_stats_with_cost = []
    for mode_stat in mode_stats:
        mode_requests = requests.filter(charging_mode=mode_stat['charging_mode'], session__isnull=False)
        cost_data = mode_requests.aggregate(
            total_cost=Sum('session__total_cost'),
            avg_cost=Avg('session__total_cost')
        )
        mode_stat.update(cost_data)
        mode_stat['mode_display'] = '快充' if mode_stat['charging_mode'] == 'fast' else '慢充'
        mode_stats_with_cost.append(mode_stat)
    
    # 按月份统计（近6个月）
    from django.db.models import TruncMonth
    monthly_stats = requests.filter(
        end_time__gte=timezone.now() - timezone.timedelta(days=180)
    ).annotate(
        month=TruncMonth('end_time')
    ).values('month').annotate(
        count=Count('id'),
        total_amount=Sum('current_amount')
    ).order_by('month')
    
    # 按星期几统计
    from django.db.models import Extract
    weekday_stats = requests.annotate(
        weekday=Extract('end_time', 'week_day')
    ).values('weekday').annotate(
        count=Count('id'),
        avg_amount=Avg('current_amount')
    ).order_by('weekday')
    
    # 按小时统计（充电习惯）
    hour_stats = requests.annotate(
        hour=Extract('end_time', 'hour')
    ).values('hour').annotate(
        count=Count('id')
    ).order_by('hour')
    
    # 最常用的充电桩
    pile_stats = requests.filter(charging_pile__isnull=False).values(
        'charging_pile__pile_id', 'charging_pile__pile_type'
    ).annotate(
        count=Count('id'),
        total_amount=Sum('current_amount')
    ).order_by('-count')[:5]
    
    # 费用分析（通过session获取）
    cost_breakdown = requests.filter(session__isnull=False).aggregate(
        total_peak_cost=Sum('session__peak_cost'),
        total_normal_cost=Sum('session__normal_cost'),
        total_valley_cost=Sum('session__valley_cost'),
        total_service_cost=Sum('session__service_cost')
    )
    
    return Response({
        'success': True,
        'data': {
            'period_days': days,
            'total_requests': total_requests,
            'statistics': {
                # 基础统计
                'total_amount': float(aggregates['total_amount'] or 0),
                'total_cost': float(aggregates['total_cost'] or 0),
                'total_duration': float(aggregates['total_duration'] or 0),
                'avg_amount': float(aggregates['avg_amount'] or 0),
                'avg_cost': float(aggregates['avg_cost'] or 0),
                'avg_duration': float(aggregates['avg_duration'] or 0),
                'max_amount': float(aggregates['max_amount'] or 0),
                'min_amount': float(aggregates['min_amount'] or 0),
                'max_cost': float(aggregates['max_cost'] or 0),
                'min_cost': float(aggregates['min_cost'] or 0),
                
                # 频率统计
                'avg_requests_per_week': round(total_requests / (days / 7), 2),
                'avg_amount_per_week': round(float(aggregates['total_amount'] or 0) / (days / 7), 2),
                
                # 按模式统计
                'mode_statistics': mode_stats_with_cost,
                
                # 月度趋势
                'monthly_trends': [
                    {
                        'month': stat['month'].strftime('%Y-%m'),
                        'count': stat['count'],
                        'total_amount': float(stat['total_amount'] or 0)
                    }
                    for stat in monthly_stats
                ],
                
                # 星期分布
                'weekday_distribution': [
                    {
                        'weekday': stat['weekday'],
                        'weekday_name': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][stat['weekday'] - 1],
                        'count': stat['count'],
                        'avg_amount': float(stat['avg_amount'] or 0)
                    }
                    for stat in weekday_stats
                ],
                
                # 小时分布（充电习惯）
                'hourly_distribution': [
                    {
                        'hour': stat['hour'],
                        'count': stat['count']
                    }
                    for stat in hour_stats
                ],
                
                # 常用充电桩
                'favorite_piles': [
                    {
                        'pile_id': stat['charging_pile__pile_id'],
                        'pile_type': '快充' if stat['charging_pile__pile_type'] == 'fast' else '慢充',
                        'usage_count': stat['count'],
                        'total_amount': float(stat['total_amount'] or 0)
                    }
                    for stat in pile_stats
                ],
                
                # 费用分析
                'cost_analysis': {
                    'peak_cost': float(cost_breakdown['total_peak_cost'] or 0),
                    'normal_cost': float(cost_breakdown['total_normal_cost'] or 0),
                    'valley_cost': float(cost_breakdown['total_valley_cost'] or 0),
                    'service_cost': float(cost_breakdown['total_service_cost'] or 0),
                    'peak_percentage': round((float(cost_breakdown['total_peak_cost'] or 0) / float(aggregates['total_cost'] or 1)) * 100, 1),
                    'normal_percentage': round((float(cost_breakdown['total_normal_cost'] or 0) / float(aggregates['total_cost'] or 1)) * 100, 1),
                    'valley_percentage': round((float(cost_breakdown['total_valley_cost'] or 0) / float(aggregates['total_cost'] or 1)) * 100, 1),
                    'service_percentage': round((float(cost_breakdown['total_service_cost'] or 0) / float(aggregates['total_cost'] or 1)) * 100, 1)
                }
            }
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def charging_summary(request):
    """用户充电概要信息 - 简化版统计，基于充电请求"""
    user = request.user
    
    # 获取所有已完成的充电请求
    all_requests = ChargingRequest.objects.filter(
        user=user, 
        current_status='completed'
    )
    
    # 近30天记录
    recent_requests = all_requests.filter(
        end_time__gte=timezone.now() - timezone.timedelta(days=30)
    )
    
    from django.db.models import Sum, Count, Avg
    
    # 基础统计
    total_requests = all_requests.count()
    recent_requests_count = recent_requests.count()
    
    if total_requests == 0:
        return Response({
            'success': True,
            'data': {
                'total_requests': 0,
                'recent_requests': 0,
                'summary': {
                    'total_amount': 0,
                    'total_cost': 0,
                    'avg_cost_per_request': 0,
                    'most_used_mode': None,
                    'recent_activity': 'inactive'
                }
            }
        })
    
    # 总体统计
    total_stats = all_requests.aggregate(
        total_amount=Sum('current_amount')
    )
    
    # 费用统计（通过session）
    cost_stats = all_requests.filter(session__isnull=False).aggregate(
        total_cost=Sum('session__total_cost'),
        avg_cost=Avg('session__total_cost')
    )
    
    # 最常用模式
    from django.db.models import Count
    mode_usage = all_requests.values('charging_mode').annotate(
        count=Count('id')
    ).order_by('-count').first()
    
    most_used_mode = None
    if mode_usage:
        most_used_mode = '快充' if mode_usage['charging_mode'] == 'fast' else '慢充'
    
    # 活跃度评估
    if recent_requests_count >= 4:
        activity_level = 'very_active'  # 非常活跃
    elif recent_requests_count >= 2:
        activity_level = 'active'       # 活跃
    elif recent_requests_count >= 1:
        activity_level = 'moderate'     # 一般
    else:
        activity_level = 'inactive'     # 不活跃
    
    # 最近一次充电
    last_request = all_requests.order_by('-end_time').first()
    last_charging_info = None
    if last_request:
        last_charging_info = {
            'date': last_request.end_time.date() if last_request.end_time else last_request.created_at.date(),
            'amount': last_request.current_amount,
            'cost': float(last_request.session.total_cost) if hasattr(last_request, 'session') and last_request.session else 0,
            'pile_type': '快充' if last_request.charging_mode == 'fast' else '慢充'
        }
    
    return Response({
        'success': True,
        'data': {
            'total_requests': total_requests,
            'recent_requests': recent_requests_count,
            'summary': {
                'total_amount': float(total_stats['total_amount'] or 0),
                'total_cost': float(cost_stats['total_cost'] or 0),
                'avg_cost_per_request': float(cost_stats['avg_cost'] or 0),
                'most_used_mode': most_used_mode,
                'activity_level': activity_level,
                'last_charging': last_charging_info
            }
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_charging_history(request):
    """导出充电历史记录（CSV格式）- 基于充电请求"""
    import csv
    from django.http import HttpResponse
    
    user = request.user
    
    queryset = ChargingRequest.objects.filter(
        user=user,
        current_status__in=['completed', 'cancelled']
    ).select_related('charging_pile', 'session')
    
    # 获取查询参数 - 与ChargingHistoryView保持一致
    pile_type = request.GET.get('pile_type')
    pile_id = request.GET.get('pile_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
    min_cost = request.GET.get('min_cost')
    max_cost = request.GET.get('max_cost')
    order_by = request.GET.get('order_by', '-start_time')
    
    # 应用筛选条件
    if pile_type and pile_type != 'all':
        queryset = queryset.filter(charging_mode=pile_type)
    if pile_id:
        queryset = queryset.filter(charging_pile__pile_id=pile_id)
    if start_date:
        queryset = queryset.filter(start_time__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(start_time__date__lte=end_date)
    if min_amount:
        queryset = queryset.filter(current_amount__gte=float(min_amount))
    if max_amount:
        queryset = queryset.filter(current_amount__lte=float(max_amount))
    if min_cost:
        queryset = queryset.filter(session__total_cost__gte=float(min_cost))
    if max_cost:
        queryset = queryset.filter(session__total_cost__lte=float(max_cost))
    
    # 排序
    valid_order_fields = [
        'start_time', '-start_time', 'current_amount', '-current_amount', 
        'created_at', '-created_at', 'session__total_cost', '-session__total_cost'
    ]
    if order_by in valid_order_fields:
        queryset = queryset.order_by(order_by)
    else:
        queryset = queryset.order_by('-created_at')
    
    # 创建CSV响应
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="charging_history_{user.username}_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    # 添加BOM以支持Excel正确显示中文
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # 写入标题行
    writer.writerow([
        '充电时间', '结束时间', '充电桩', '充电模式', '充电量(kWh)', 
        '充电时长(小时)', '峰时费用', '平时费用', '谷时费用', 
        '服务费', '总费用', '队列号'
    ])
    
    # 写入数据行
    for request in queryset:
        # 获取会话数据（如果存在）
        session = getattr(request, 'session', None)
        
        writer.writerow([
            request.start_time.strftime('%Y-%m-%d %H:%M:%S') if request.start_time else '',
            request.end_time.strftime('%Y-%m-%d %H:%M:%S') if request.end_time else '',
            request.charging_pile.pile_id if request.charging_pile else '',
            '快充' if request.charging_mode == 'fast' else '慢充',
            request.current_amount,
            round(session.charging_duration, 2) if session else 0,
            float(session.peak_cost) if session else 0,
            float(session.normal_cost) if session else 0,
            float(session.valley_cost) if session else 0,
            float(session.service_cost) if session else 0,
            float(session.total_cost) if session else 0,
            request.queue_number
        ])
    
    return response

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
@permission_classes([IsAuthenticated])
def active_charging_requests(request):
    """获取当前用户的所有活跃充电请求"""
    try:
        charging_requests = ChargingRequest.objects.filter(
            user=request.user,
            current_status__in=['waiting', 'charging']
        ).order_by('created_at')
        
        if not charging_requests.exists():
            return Response({
                'success': True,
                'data': []
            })
        
        # 为每个请求计算前面等待的数量和状态信息
        results = []
        for charging_request in charging_requests:
            # 根据队列层级计算前面等待的数量
            ahead_count = 0
            if charging_request.queue_level == 'external_waiting':
                ahead_count = charging_request.external_queue_position - 1
            elif charging_request.queue_level == 'pile_queue':
                ahead_count = charging_request.pile_queue_position - 1
            
            data = ChargingRequestSerializer(charging_request).data
            data['ahead_count'] = ahead_count
            data['queue_status'] = charging_request.get_queue_status_display()
            data['queue_level'] = charging_request.queue_level
            
            results.append(data)
        
        return Response({
            'success': True,
            'data': results
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': f'查询活跃充电请求失败: {str(e)}'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
