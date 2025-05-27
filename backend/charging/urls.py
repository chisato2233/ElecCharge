# backend/charging/urls.py
from django.urls import path
from . import views

app_name = 'charging'

urlpatterns = [
    # 充电请求管理
    path('request/', views.ChargingRequestView.as_view(), name='charging_request'),
    path('request/<uuid:request_id>/', views.modify_charging_request, name='modify_request'),
    path('request/<uuid:request_id>/cancel/', views.cancel_charging_request, name='cancel_request'),
    path('request/status/', views.charging_request_status, name='request_status'),
    path('complete/', views.complete_charging, name='complete_charging'),
    
    # 排队信息
    path('queue/status/', views.queue_status, name='queue_status'),
    path('piles/status/', views.piles_status, name='piles_status'),
    
    # 账单管理
    path('bills/', views.BillListView.as_view(), name='bills'),
    path('bills/<uuid:bill_id>/', views.bill_detail, name='bill_detail'),
    
    # 通知
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_read'),
]