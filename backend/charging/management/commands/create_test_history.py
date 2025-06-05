from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from charging.models import ChargingPile, ChargingRequest, ChargingSession
from datetime import datetime, timedelta
from decimal import Decimal
import random

User = get_user_model()

class Command(BaseCommand):
    help = '创建测试充电历史数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='创建的记录数量'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # 获取或创建测试用户
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': '测试',
                'last_name': '用户'
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(f"创建了测试用户: {user.username}")
        else:
            self.stdout.write(f"使用现有测试用户: {user.username}")
        
        # 获取充电桩
        fast_piles = ChargingPile.objects.filter(pile_type='fast')
        slow_piles = ChargingPile.objects.filter(pile_type='slow')
        
        if not fast_piles.exists() or not slow_piles.exists():
            self.stdout.write(self.style.WARNING("警告: 没有找到充电桩，请先运行初始化数据脚本"))
            return
        
        # 清除该用户的旧测试数据
        old_sessions = ChargingSession.objects.filter(user=user)
        old_requests = ChargingRequest.objects.filter(user=user)
        
        if old_sessions.exists() or old_requests.exists():
            self.stdout.write(f"清除 {old_sessions.count()} 个旧充电会话和 {old_requests.count()} 个旧请求")
            old_sessions.delete()
            old_requests.delete()
        
        # 创建一些历史充电记录
        sessions_to_create = []
        requests_to_create = []
        
        # 创建过去30天的随机充电记录
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(count):
            # 随机选择充电桩
            if random.choice([True, False]):
                pile = random.choice(fast_piles)
                charging_mode = 'fast'
                avg_power = 120  # kW
            else:
                pile = random.choice(slow_piles)
                charging_mode = 'slow'
                avg_power = 7   # kW
            
            # 随机生成充电参数
            requested_amount = random.uniform(20, 80)  # 20-80 kWh
            charging_amount = requested_amount * random.uniform(0.95, 1.0)  # 95-100%的完成度
            charging_duration = charging_amount / avg_power  # 小时
            
            # 随机生成时间
            days_ago = random.randint(1, 30)
            hour = random.randint(8, 22)  # 8点到22点
            start_time = base_date + timedelta(days=days_ago, hours=hour)
            end_time = start_time + timedelta(hours=charging_duration)
            
            # 生成队列号
            prefix = 'F' if charging_mode == 'fast' else 'S'
            timestamp = start_time.strftime('%m%d%H%M')
            queue_number = f"{prefix}{timestamp}{i+1:03d}"
            
            # 创建充电请求
            request = ChargingRequest(
                user=user,
                queue_number=queue_number,
                charging_mode=charging_mode,
                requested_amount=requested_amount,
                battery_capacity=random.uniform(60, 100),  # 60-100 kWh电池
                current_status='completed',
                charging_pile=pile,
                start_time=start_time,
                end_time=end_time,
                current_amount=charging_amount,
                created_at=start_time - timedelta(minutes=random.randint(5, 30))
            )
            request.save()  # 先保存request
            
            # 计算费用（简化计算）
            # 假设峰时:8-12,18-22, 平时:12-18, 谷时:22-8
            peak_hours = 0
            normal_hours = 0
            valley_hours = 0
            
            current_time = start_time
            remaining_duration = charging_duration
            
            while remaining_duration > 0:
                hour_of_day = current_time.hour
                
                # 判断时段
                if (8 <= hour_of_day < 12) or (18 <= hour_of_day < 22):
                    time_type = 'peak'
                elif 12 <= hour_of_day < 18:
                    time_type = 'normal'
                else:
                    time_type = 'valley'
                
                # 计算这个小时内的充电时间
                time_in_hour = min(remaining_duration, 1.0)
                
                if time_type == 'peak':
                    peak_hours += time_in_hour
                elif time_type == 'normal':
                    normal_hours += time_in_hour
                else:
                    valley_hours += time_in_hour
                
                remaining_duration -= time_in_hour
                current_time += timedelta(hours=1)
            
            # 费用计算（使用固定费率）
            peak_rate = Decimal('1.2')      # 峰时电价
            normal_rate = Decimal('0.8')    # 平时电价
            valley_rate = Decimal('0.4')    # 谷时电价
            service_rate = Decimal('0.2')   # 服务费
            
            peak_cost = Decimal(str(peak_hours)) * Decimal(str(charging_amount / charging_duration)) * peak_rate
            normal_cost = Decimal(str(normal_hours)) * Decimal(str(charging_amount / charging_duration)) * normal_rate
            valley_cost = Decimal(str(valley_hours)) * Decimal(str(charging_amount / charging_duration)) * valley_rate
            service_cost = Decimal(str(charging_amount)) * service_rate
            
            total_cost = peak_cost + normal_cost + valley_cost + service_cost
            
            # 创建充电会话
            session = ChargingSession(
                request=request,
                pile=pile,
                user=user,
                start_time=start_time,
                end_time=end_time,
                charging_amount=charging_amount,
                charging_duration=charging_duration,
                peak_hours=peak_hours,
                normal_hours=normal_hours,
                valley_hours=valley_hours,
                peak_cost=peak_cost,
                normal_cost=normal_cost,
                valley_cost=valley_cost,
                service_cost=service_cost,
                total_cost=total_cost,
                created_at=end_time
            )
            session.save()
            
            if (i + 1) % 5 == 0:
                self.stdout.write(f"已创建 {i + 1}/{count} 个记录...")
        
        self.stdout.write(
            self.style.SUCCESS(f"成功创建了 {count} 个充电记录")
        )
        self.stdout.write(f"测试用户: {user.username} (密码: testpass123)")
        self.stdout.write("现在可以登录并在历史记录页面查看这些数据") 