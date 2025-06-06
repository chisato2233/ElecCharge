from django.core.management.base import BaseCommand
from django.db import transaction
from charging.models import ChargingRequest, ChargingPile

class Command(BaseCommand):
    help = '将现有数据迁移到多级队列系统'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始迁移数据到多级队列系统...'))
        
        # 1. 更新充电桩功率信息
        self.update_pile_power()
        
        # 2. 迁移充电请求的队列信息
        self.migrate_charging_requests()
        
        self.stdout.write(self.style.SUCCESS('数据迁移完成！'))

    def update_pile_power(self):
        """更新充电桩功率信息"""
        self.stdout.write('更新充电桩功率信息...')
        
        # 更新快充桩功率
        fast_piles_updated = ChargingPile.objects.filter(
            pile_type='fast',
            charging_power=120.0  # 默认值
        ).update(charging_power=120.0)
        
        # 更新慢充桩功率
        slow_piles_updated = ChargingPile.objects.filter(
            pile_type='slow'
        ).update(charging_power=7.0)
        
        # 更新队列容量
        ChargingPile.objects.filter(pile_type='fast').update(max_queue_size=3)
        ChargingPile.objects.filter(pile_type='slow').update(max_queue_size=5)
        
        self.stdout.write(f'  更新了快充桩功率: {fast_piles_updated} 个')
        self.stdout.write(f'  更新了慢充桩功率: {slow_piles_updated} 个')

    def migrate_charging_requests(self):
        """迁移充电请求的队列信息"""
        self.stdout.write('迁移充电请求队列信息...')
        
        with transaction.atomic():
            # 获取所有活跃的充电请求
            active_requests = ChargingRequest.objects.filter(
                current_status__in=['waiting', 'charging']
            )
            
            for request in active_requests:
                if request.current_status == 'charging':
                    # 正在充电的请求设置为charging级别
                    request.queue_level = 'charging'
                    request.external_queue_position = 0
                    request.pile_queue_position = 0
                elif request.current_status == 'waiting':
                    if request.charging_pile:
                        # 已分配充电桩的设置为桩队列
                        request.queue_level = 'pile_queue'
                        request.external_queue_position = 0
                        
                        # 计算在桩队列中的位置
                        pile_queue_count = ChargingRequest.objects.filter(
                            charging_pile=request.charging_pile,
                            current_status='waiting',
                            id__lt=request.id  # 比当前请求更早的
                        ).count()
                        request.pile_queue_position = pile_queue_count + 1
                    else:
                        # 未分配充电桩的设置为外部等候区
                        request.queue_level = 'external_waiting'
                        request.pile_queue_position = 0
                        
                        # 计算在外部等候区的位置
                        external_queue_count = ChargingRequest.objects.filter(
                            charging_mode=request.charging_mode,
                            current_status='waiting',
                            charging_pile__isnull=True,
                            id__lt=request.id  # 比当前请求更早的
                        ).count()
                        request.external_queue_position = external_queue_count + 1
                
                request.save()
            
            # 处理已完成的请求
            completed_requests = ChargingRequest.objects.filter(
                current_status__in=['completed', 'cancelled']
            )
            
            for request in completed_requests:
                request.queue_level = 'completed'
                request.external_queue_position = 0
                request.pile_queue_position = 0
                request.save()
            
            self.stdout.write(f'  迁移了 {active_requests.count()} 个活跃请求')
            self.stdout.write(f'  迁移了 {completed_requests.count()} 个已完成请求')

    def handle_error(self, e):
        """错误处理"""
        self.stdout.write(
            self.style.ERROR(f'迁移过程中发生错误: {str(e)}')
        )
        raise e 