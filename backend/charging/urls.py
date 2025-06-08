# backend/charging/urls.py
from django.urls import path
from . import views

app_name = 'charging'

urlpatterns = [
    # 公开接口
    path('status/', views.public_system_status, name='public_status'),
    
    # 充电请求管理
    path('request/', views.ChargingRequestView.as_view(), name='charging_request'),
    path('request/<uuid:request_id>/', views.modify_charging_request, name='modify_request'),
    path('request/<uuid:request_id>/cancel/', views.cancel_charging_request, name='cancel_request'),
    path('request/<uuid:request_id>/change-mode/', views.change_charging_mode, name='change_charging_mode'),
    path('request/status/', views.charging_request_status, name='request_status'),
    path('requests/active/', views.active_charging_requests, name='active_requests'),
    path('complete/', views.complete_charging, name='complete_charging'),
    
    # 充电进度控制
    path('progress/update/', views.update_charging_progress, name='update_progress'),
    
    # 排队信息
    path('queue/status/', views.queue_status, name='queue_status'),
    path('piles/status/', views.piles_status, name='piles_status'),
    path('queue/enhanced/', views.enhanced_queue_status, name='enhanced_queue_status'),
    
    # 账单管理
    path('bills/', views.BillListView.as_view(), name='bills'),
    path('bills/<uuid:bill_id>/', views.bill_detail, name='bill_detail'),
    
    # 历史记录管理
    path('history/', views.ChargingHistoryView.as_view(), name='charging_history'),
    path('history/statistics/', views.charging_statistics, name='charging_statistics'),
    path('history/summary/', views.charging_summary, name='charging_summary'),
    path('history/export/', views.export_charging_history, name='export_history'),
    
    # 通知
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_read'),
    
    # 系统参数
    path('system_parameters/', views.system_parameters, name='system_parameters'),
]