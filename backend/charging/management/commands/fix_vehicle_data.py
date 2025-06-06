from django.core.management.base import BaseCommand
from django.db import transaction
from charging.models import ChargingRequest, ChargingSession
from accounts.models import Vehicle


class Command(BaseCommand):
    help = '修复现有充电请求和会话的车辆关联数据'

    def handle(self, *args, **options):
        self.stdout.write('开始修复车辆关联数据...')
        
        with transaction.atomic():
            # 修复充电请求
            requests_fixed = 0
            for request in ChargingRequest.objects.filter(vehicle__isnull=True):
                # 为每个用户分配默认车辆或第一辆车
                default_vehicle = Vehicle.objects.filter(
                    user=request.user, 
                    is_default=True
                ).first()
                
                if not default_vehicle:
                    default_vehicle = Vehicle.objects.filter(
                        user=request.user
                    ).first()
                
                if default_vehicle:
                    request.vehicle = default_vehicle
                    request.save()
                    requests_fixed += 1
                    self.stdout.write(f'修复请求 {request.queue_number} -> 车辆 {default_vehicle.license_plate}')
                else:
                    self.stdout.write(
                        self.style.WARNING(f'用户 {request.user.username} 没有车辆，跳过请求 {request.queue_number}')
                    )
            
            # 修复充电会话
            sessions_fixed = 0
            for session in ChargingSession.objects.filter(vehicle__isnull=True):
                if session.request and session.request.vehicle:
                    session.vehicle = session.request.vehicle
                    session.save()
                    sessions_fixed += 1
                    self.stdout.write(f'修复会话 {session.id} -> 车辆 {session.request.vehicle.license_plate}')
                else:
                    # 尝试为用户分配默认车辆
                    default_vehicle = Vehicle.objects.filter(
                        user=session.user, 
                        is_default=True
                    ).first()
                    
                    if not default_vehicle:
                        default_vehicle = Vehicle.objects.filter(
                            user=session.user
                        ).first()
                    
                    if default_vehicle:
                        session.vehicle = default_vehicle
                        session.save()
                        sessions_fixed += 1
                        self.stdout.write(f'修复会话 {session.id} -> 车辆 {default_vehicle.license_plate}')
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'用户 {session.user.username} 没有车辆，跳过会话 {session.id}')
                        )
        
        self.stdout.write(
            self.style.SUCCESS(f'修复完成！修复了 {requests_fixed} 个请求和 {sessions_fixed} 个会话')
        ) 