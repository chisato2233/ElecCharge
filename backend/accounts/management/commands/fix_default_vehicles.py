from django.core.management.base import BaseCommand
from django.db.models import Count
from accounts.models import User, Vehicle


class Command(BaseCommand):
    help = '修复用户有多个默认车辆的问题，确保每个用户只有一个默认车辆'

    def handle(self, *args, **options):
        self.stdout.write('开始修复默认车辆数据...')
        
        fixed_count = 0
        
        # 找到有多个默认车辆的用户
        users_with_multiple_defaults = User.objects.annotate(
            default_count=Count('vehicles', filter={'vehicles__is_default': True})
        ).filter(default_count__gt=1)
        
        for user in users_with_multiple_defaults:
            self.stdout.write(f'处理用户: {user.username} (ID: {user.id})')
            
            # 获取该用户的所有默认车辆，按创建时间排序
            default_vehicles = Vehicle.objects.filter(
                user=user, 
                is_default=True
            ).order_by('created_at')
            
            # 保留最早创建的车辆作为默认车辆，其他设为非默认
            vehicles_to_update = default_vehicles[1:]  # 除了第一个外的所有车辆
            
            for vehicle in vehicles_to_update:
                vehicle.is_default = False
                vehicle.save()
                self.stdout.write(f'  - 车辆 {vehicle.license_plate} 已设为非默认')
                fixed_count += 1
        
        # 为没有默认车辆的用户设置默认车辆
        users_without_default = User.objects.annotate(
            default_count=Count('vehicles', filter={'vehicles__is_default': True})
        ).filter(default_count=0, vehicles__isnull=False)
        
        for user in users_without_default:
            first_vehicle = Vehicle.objects.filter(user=user).order_by('created_at').first()
            if first_vehicle:
                first_vehicle.is_default = True
                first_vehicle.save()
                self.stdout.write(f'为用户 {user.username} 设置默认车辆: {first_vehicle.license_plate}')
                fixed_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'默认车辆数据修复完成！共修复 {fixed_count} 个车辆记录')
        ) 