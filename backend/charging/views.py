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
                
                # 释放充电桩
                if charging_request.charging_pile:
                    pile = charging_request.charging_pile
                    pile.is_working = False
                    pile.save()
                    
                    queue_service = ChargingQueueService()
                    queue_service.process_next_in_queue(pile)
                
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
def queue_status(request):
    """获取排队状态"""
    # 快充排队
    fast_queue = ChargingRequest.objects.filter(
        charging_mode='fast',
        current_status='waiting'
    ).order_by('queue_position')
    
    # 慢充排队
    slow_queue = ChargingRequest.objects.filter(
        charging_mode='slow', 
        current_status='waiting'
    ).order_by('queue_position')
    
    # 等候区容量
    try:
        waiting_area_max = SystemParameter.objects.get(
            param_key='WaitingAreaSize'
        ).get_value()
    except SystemParameter.DoesNotExist:
        waiting_area_max = 10
    
    waiting_area_current = ChargingRequest.objects.filter(
        current_status='waiting'
    ).count()
    
    return Response({
        'success': True,
        'data': {
            'fast_charging': {
                'waiting_count': fast_queue.count(),
                'queue_list': [
                    {
                        'queue_number': req.queue_number,
                        'estimated_wait_time': req.estimated_wait_time
                    }
                    for req in fast_queue[:5]  # 显示前5个
                ]
            },
            'slow_charging': {
                'waiting_count': slow_queue.count(),
                'queue_list': [
                    {
                        'queue_number': req.queue_number,
                        'estimated_wait_time': req.estimated_wait_time
                    }
                    for req in slow_queue[:5]
                ]
            },
            'waiting_area_capacity': {
                'current': waiting_area_current,
                'max': waiting_area_max
            }
        }
    })

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
        
        return Response({
            'success': True,
            'data': {
                'pricing': pricing_params,
                'capacity': capacity_params
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
    """用户充电历史记录视图 - 扩展版本"""
    serializer_class = ChargingSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = ChargingSession.objects.filter(user=self.request.user)
        
        # 多种筛选条件
        pile_type = self.request.query_params.get('pile_type')  # fast/slow
        pile_id = self.request.query_params.get('pile_id')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        min_amount = self.request.query_params.get('min_amount')
        max_amount = self.request.query_params.get('max_amount')
        min_cost = self.request.query_params.get('min_cost')
        max_cost = self.request.query_params.get('max_cost')
        
        # 只有当pile_type存在且不为'all'时才应用筛选
        if pile_type and pile_type != 'all':
            queryset = queryset.filter(pile__pile_type=pile_type)
        if pile_id:
            queryset = queryset.filter(pile__pile_id=pile_id)
        if start_date:
            queryset = queryset.filter(start_time__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__date__lte=end_date)
        if min_amount:
            queryset = queryset.filter(charging_amount__gte=float(min_amount))
        if max_amount:
            queryset = queryset.filter(charging_amount__lte=float(max_amount))
        if min_cost:
            queryset = queryset.filter(total_cost__gte=float(min_cost))
        if max_cost:
            queryset = queryset.filter(total_cost__lte=float(max_cost))
            
        # 排序
        order_by = self.request.query_params.get('order_by', '-start_time')
        if order_by in ['start_time', '-start_time', 'charging_amount', '-charging_amount', 
                       'total_cost', '-total_cost', 'charging_duration', '-charging_duration']:
            queryset = queryset.order_by(order_by)
        else:
            queryset = queryset.order_by('-start_time')
            
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
    """用户充电统计分析"""
    user = request.user
    
    # 时间范围参数
    days = int(request.GET.get('days', 30))  # 默认30天
    start_date = timezone.now() - timezone.timedelta(days=days)
    
    # 基础查询
    sessions = ChargingSession.objects.filter(
        user=user,
        start_time__gte=start_date
    )
    
    # 基础统计
    total_sessions = sessions.count()
    if total_sessions == 0:
        return Response({
            'success': True,
            'data': {
                'period_days': days,
                'total_sessions': 0,
                'statistics': None
            }
        })
    
    from django.db.models import Sum, Avg, Count, Max, Min
    from decimal import Decimal
    
    # 聚合统计
    aggregates = sessions.aggregate(
        total_amount=Sum('charging_amount'),
        total_cost=Sum('total_cost'),
        total_duration=Sum('charging_duration'),
        avg_amount=Avg('charging_amount'),
        avg_cost=Avg('total_cost'),
        avg_duration=Avg('charging_duration'),
        max_amount=Max('charging_amount'),
        min_amount=Min('charging_amount'),
        max_cost=Max('total_cost'),
        min_cost=Min('total_cost')
    )
    
    # 按充电模式统计
    mode_stats = sessions.values('pile__pile_type').annotate(
        count=Count('id'),
        total_amount=Sum('charging_amount'),
        total_cost=Sum('total_cost'),
        avg_amount=Avg('charging_amount'),
        avg_cost=Avg('total_cost')
    )
    
    # 按月份统计（近6个月）
    from django.db.models import TruncMonth
    monthly_stats = sessions.filter(
        start_time__gte=timezone.now() - timezone.timedelta(days=180)
    ).annotate(
        month=TruncMonth('start_time')
    ).values('month').annotate(
        count=Count('id'),
        total_amount=Sum('charging_amount'),
        total_cost=Sum('total_cost')
    ).order_by('month')
    
    # 按星期几统计
    from django.db.models import Extract
    weekday_stats = sessions.annotate(
        weekday=Extract('start_time', 'week_day')
    ).values('weekday').annotate(
        count=Count('id'),
        avg_amount=Avg('charging_amount')
    ).order_by('weekday')
    
    # 按小时统计（充电习惯）
    hour_stats = sessions.annotate(
        hour=Extract('start_time', 'hour')
    ).values('hour').annotate(
        count=Count('id')
    ).order_by('hour')
    
    # 最常用的充电桩
    pile_stats = sessions.values(
        'pile__pile_id', 'pile__pile_type'
    ).annotate(
        count=Count('id'),
        total_amount=Sum('charging_amount')
    ).order_by('-count')[:5]
    
    # 费用分析
    cost_breakdown = sessions.aggregate(
        total_peak_cost=Sum('peak_cost'),
        total_normal_cost=Sum('normal_cost'),
        total_valley_cost=Sum('valley_cost'),
        total_service_cost=Sum('service_cost')
    )
    
    return Response({
        'success': True,
        'data': {
            'period_days': days,
            'total_sessions': total_sessions,
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
                'avg_sessions_per_week': round(total_sessions / (days / 7), 2),
                'avg_amount_per_week': round(float(aggregates['total_amount'] or 0) / (days / 7), 2),
                
                # 按模式统计
                'mode_statistics': [
                    {
                        'mode': stat['pile__pile_type'],
                        'mode_name': '快充' if stat['pile__pile_type'] == 'fast' else '慢充',
                        'count': stat['count'],
                        'total_amount': float(stat['total_amount'] or 0),
                        'total_cost': float(stat['total_cost'] or 0),
                        'avg_amount': float(stat['avg_amount'] or 0),
                        'avg_cost': float(stat['avg_cost'] or 0),
                        'percentage': round((stat['count'] / total_sessions) * 100, 1)
                    }
                    for stat in mode_stats
                ],
                
                # 月度趋势
                'monthly_trends': [
                    {
                        'month': stat['month'].strftime('%Y-%m'),
                        'count': stat['count'],
                        'total_amount': float(stat['total_amount'] or 0),
                        'total_cost': float(stat['total_cost'] or 0)
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
                        'pile_id': stat['pile__pile_id'],
                        'pile_type': '快充' if stat['pile__pile_type'] == 'fast' else '慢充',
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
    """用户充电概要信息 - 简化版统计"""
    user = request.user
    
    # 获取所有充电记录
    all_sessions = ChargingSession.objects.filter(user=user)
    
    # 近30天记录
    recent_sessions = all_sessions.filter(
        start_time__gte=timezone.now() - timezone.timedelta(days=30)
    )
    
    from django.db.models import Sum, Count, Avg
    
    # 基础统计
    total_sessions = all_sessions.count()
    recent_sessions_count = recent_sessions.count()
    
    if total_sessions == 0:
        return Response({
            'success': True,
            'data': {
                'total_sessions': 0,
                'recent_sessions': 0,
                'summary': {
                    'total_amount': 0,
                    'total_cost': 0,
                    'avg_cost_per_session': 0,
                    'most_used_mode': None,
                    'recent_activity': 'inactive'
                }
            }
        })
    
    # 总体统计
    total_stats = all_sessions.aggregate(
        total_amount=Sum('charging_amount'),
        total_cost=Sum('total_cost')
    )
    
    # 分别计算平均费用，避免聚合冲突
    avg_cost = 0
    if total_sessions > 0:
        avg_cost_result = all_sessions.aggregate(avg_cost=Avg('total_cost'))
        avg_cost = avg_cost_result['avg_cost'] or 0
    
    # 最常用模式
    from django.db.models import Count
    mode_usage = all_sessions.values('pile__pile_type').annotate(
        count=Count('id')
    ).order_by('-count').first()
    
    most_used_mode = None
    if mode_usage:
        most_used_mode = '快充' if mode_usage['pile__pile_type'] == 'fast' else '慢充'
    
    # 活跃度评估
    if recent_sessions_count >= 4:
        activity_level = 'very_active'  # 非常活跃
    elif recent_sessions_count >= 2:
        activity_level = 'active'       # 活跃
    elif recent_sessions_count >= 1:
        activity_level = 'moderate'     # 一般
    else:
        activity_level = 'inactive'     # 不活跃
    
    # 最近一次充电
    last_session = all_sessions.order_by('-start_time').first()
    last_charging_info = None
    if last_session:
        last_charging_info = {
            'date': last_session.start_time.date(),
            'amount': last_session.charging_amount,
            'cost': float(last_session.total_cost),
            'pile_type': '快充' if last_session.pile.pile_type == 'fast' else '慢充'
        }
    
    return Response({
        'success': True,
        'data': {
            'total_sessions': total_sessions,
            'recent_sessions': recent_sessions_count,
            'summary': {
                'total_amount': float(total_stats['total_amount'] or 0),
                'total_cost': float(total_stats['total_cost'] or 0),
                'avg_cost_per_session': avg_cost,
                'most_used_mode': most_used_mode,
                'activity_level': activity_level,
                'last_charging': last_charging_info
            }
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_charging_history(request):
    """导出充电历史记录（CSV格式）"""
    import csv
    from django.http import HttpResponse
    
    user = request.user
    
    queryset = ChargingSession.objects.filter(user=user)
    
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
        queryset = queryset.filter(pile__pile_type=pile_type)
    if pile_id:
        queryset = queryset.filter(pile__pile_id=pile_id)
    if start_date:
        queryset = queryset.filter(start_time__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(start_time__date__lte=end_date)
    if min_amount:
        queryset = queryset.filter(charging_amount__gte=float(min_amount))
    if max_amount:
        queryset = queryset.filter(charging_amount__lte=float(max_amount))
    if min_cost:
        queryset = queryset.filter(total_cost__gte=float(min_cost))
    if max_cost:
        queryset = queryset.filter(total_cost__lte=float(max_cost))
    
    # 排序
    if order_by in ['start_time', '-start_time', 'charging_amount', '-charging_amount', 
                   'total_cost', '-total_cost', 'charging_duration', '-charging_duration']:
        queryset = queryset.order_by(order_by)
    else:
        queryset = queryset.order_by('-start_time')
    
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
    for session in queryset:
        writer.writerow([
            session.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            session.end_time.strftime('%Y-%m-%d %H:%M:%S') if session.end_time else '',
            session.pile.pile_id,
            '快充' if session.pile.pile_type == 'fast' else '慢充',
            session.charging_amount,
            round(session.charging_duration, 2),
            float(session.peak_cost),
            float(session.normal_cost),
            float(session.valley_cost),
            float(session.service_cost),
            float(session.total_cost),
            session.request.queue_number if session.request else ''
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
