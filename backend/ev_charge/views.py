# backend/ev_charge/views.py
import django
import sys
import platform
from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
from accounts.models import User
import os

def home(request):
    """系统状态首页"""
    
    # 获取系统信息
    context = {
        'django_version': django.get_version(),
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'debug_mode': '开启' if settings.DEBUG else '关闭',
        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    # 数据库状态检查
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            context['db_status'] = '● 连接正常'
            context['db_engine'] = 'MySQL'
            context['db_name'] = settings.DATABASES['default']['NAME']
    except Exception as e:
        context['db_status'] = '● 连接异常'
        context['db_engine'] = '未知'
        context['db_name'] = '未知'
    
    # 用户统计
    try:
        context['user_count'] = User.objects.count()
        # 活跃用户（最近7天登录的用户）
        week_ago = datetime.now() - timedelta(days=7)
        context['active_users'] = User.objects.filter(last_login__gte=week_ago).count()
    except Exception:
        context['user_count'] = 0
        context['active_users'] = 0
    
    # 充电站配置（从环境变量或默认值获取）
    context['fast_piles_count'] = os.getenv('FastChargingPileNum', '2')
    context['slow_piles_count'] = os.getenv('TrickleChargingPileNum', '3')
    context['waiting_area_size'] = os.getenv('WaitingAreaSize', '6')
    
    # 模拟一些统计数据
    context['current_queue_count'] = 0  # 当前排队数量
    context['today_sessions'] = 0  # 今日充电次数
    context['uptime'] = '运行中'  # 系统运行时间
    context['last_update'] = datetime.now().strftime('%H:%M:%S')
    
    return render(request, 'home.html', context)

def health_check(request):
    """健康检查API"""
    try:
        # 检查数据库连接
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # 检查用户表
        user_count = User.objects.count()
        
        return JsonResponse({
            "status": "healthy",
            "service": "ev_charge_backend",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "user_count": user_count,
            "version": "1.0.0"
        })
    except Exception as e:
        return JsonResponse({
            "status": "unhealthy",
            "service": "ev_charge_backend",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }, status=503)

def api_home(request):
    """API首页 - JSON格式"""
    return JsonResponse({
        "message": "EV Charge Backend API", 
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "home": "/",
            "admin": "/admin/",
            "health": "/health/",
            "auth": "/api/auth/",
            "charging": "/api/charging/",
            "config": "/api/config/"
        }
    })