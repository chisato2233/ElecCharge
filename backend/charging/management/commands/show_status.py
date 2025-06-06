from django.core.management.base import BaseCommand
from charging.models import ChargingPile, SystemParameter, ChargingRequest
from django.utils import timezone

class Command(BaseCommand):
    help = '显示系统当前状态和参数配置'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('📊 当前系统状态和参数配置'))
        self.stdout.write('=' * 50)
        
        self.show_system_parameters()
        self.show_charging_piles()
        self.show_queue_status()
        self.show_statistics()

    def show_system_parameters(self):
        """显示系统参数"""
        self.stdout.write('\n🔧 === 系统参数配置 ===')
        
        # 分类显示参数（使用新的统一命名）
        categories = {
            '充电桩配置': [
                'fast_charging_pile_num', 'slow_charging_pile_num', 
                'fast_charging_power', 'slow_charging_power'
            ],
            '队列管理': [
                'external_waiting_area_size', 'fast_pile_max_queue_size', 
                'slow_pile_max_queue_size', 'queue_position_update_interval'
            ],
            '电价费率': [
                'peak_rate', 'normal_rate', 'valley_rate', 'service_rate'
            ],
            '时间段配置': [
                'peak_hours_start', 'peak_hours_end',
                'valley_hours_start', 'valley_hours_end'
            ],
            '系统配置': [
                'max_charging_time_per_session', 'notification_enabled',
                'auto_queue_management', 'shortest_wait_time_threshold'
            ]
        }
        
        for category, param_keys in categories.items():
            self.stdout.write(f'\n📋 {category}:')
            for key in param_keys:
                try:
                    param = SystemParameter.objects.get(param_key=key)
                    unit = self.get_param_unit(key)
                    # 布尔值特殊处理
                    if param.param_type == 'boolean':
                        value = '启用' if param.param_value.lower() == 'true' else '禁用'
                        self.stdout.write(f'   {key}: {value} ({param.param_type})')
                    else:
                        self.stdout.write(f'   {key}: {param.param_value}{unit} ({param.param_type})')
                    if param.description:
                        self.stdout.write(f'      └─ {param.description}')
                except SystemParameter.DoesNotExist:
                    self.stdout.write(f'   {key}: ❌ 未设置')

    def get_param_unit(self, param_key):
        """获取参数单位"""
        units = {
            'fast_charging_pile_num': '个',
            'slow_charging_pile_num': '个',
            'external_waiting_area_size': '人',
            'fast_pile_max_queue_size': '人',
            'slow_pile_max_queue_size': '人',
            'queue_position_update_interval': '秒',
            'fast_charging_power': 'kW',
            'slow_charging_power': 'kW',
            'peak_rate': '元/kWh',
            'normal_rate': '元/kWh',
            'valley_rate': '元/kWh',
            'service_rate': '元/kWh',
            'max_charging_time_per_session': '分钟',
            'shortest_wait_time_threshold': '分钟',
            'maintenance_check_interval': '小时'
        }
        return units.get(param_key, '')

    def show_charging_piles(self):
        """显示充电桩状态"""
        self.stdout.write('\n⚡ === 充电桩状态 ===')
        
        # 按类型分组显示
        for pile_type, type_name in [('fast', '快充桩'), ('slow', '慢充桩')]:
            piles = ChargingPile.objects.filter(pile_type=pile_type).order_by('pile_id')
            if piles.exists():
                self.stdout.write(f'\n🔌 {type_name} ({piles.count()}个):')
                for pile in piles:
                    status_icon = '🔴' if pile.is_working else '🟢'
                    status_text = '工作中' if pile.is_working else '空闲'
                    
                    # 获取当前充电请求
                    current_request = None
                    if pile.is_working:
                        current_request = ChargingRequest.objects.filter(
                            charging_pile=pile,
                            current_status='charging'
                        ).first()
                    
                    self.stdout.write(
                        f'   {status_icon} {pile.pile_id}: '
                        f'功率{pile.charging_power}kW, '
                        f'队列容量{pile.max_queue_size}, '
                        f'状态:{status_text}'
                    )
                    
                    if current_request:
                        progress = (current_request.current_amount / current_request.requested_amount) * 100
                        self.stdout.write(
                            f'      └─ 正在充电: {current_request.queue_number} '
                            f'({current_request.user.username}), '
                            f'进度: {progress:.1f}%'
                        )
                    
                    # 显示队列情况
                    queue_requests = ChargingRequest.objects.filter(
                        charging_pile=pile,
                        queue_level='pile_queue'
                    ).count()
                    
                    if queue_requests > 0:
                        self.stdout.write(f'      └─ 队列等待: {queue_requests}人')
            else:
                self.stdout.write(f'\n🔌 {type_name}: 无')

    def show_queue_status(self):
        """显示队列状态"""
        self.stdout.write('\n👥 === 队列状态 ===')
        
        # 外部等候区
        external_waiting = ChargingRequest.objects.filter(queue_level='external_waiting')
        fast_external = external_waiting.filter(charging_mode='fast').count()
        slow_external = external_waiting.filter(charging_mode='slow').count()
        
        self.stdout.write(f'🕐 外部等候区:')
        self.stdout.write(f'   快充等待: {fast_external}人')
        self.stdout.write(f'   慢充等待: {slow_external}人')
        self.stdout.write(f'   总计等待: {fast_external + slow_external}人')
        
        # 桩队列
        pile_queue = ChargingRequest.objects.filter(queue_level='pile_queue')
        fast_pile_queue = pile_queue.filter(charging_mode='fast').count()
        slow_pile_queue = pile_queue.filter(charging_mode='slow').count()
        
        self.stdout.write(f'📍 桩队列:')
        self.stdout.write(f'   快充桩队列: {fast_pile_queue}人')
        self.stdout.write(f'   慢充桩队列: {slow_pile_queue}人')
        self.stdout.write(f'   总计排队: {fast_pile_queue + slow_pile_queue}人')
        
        # 正在充电
        charging = ChargingRequest.objects.filter(current_status='charging').count()
        self.stdout.write(f'⚡ 正在充电: {charging}人')

    def show_statistics(self):
        """显示统计信息"""
        self.stdout.write('\n📈 === 系统统计 ===')
        
        # 充电桩统计
        total_piles = ChargingPile.objects.count()
        working_piles = ChargingPile.objects.filter(is_working=True).count()
        available_piles = total_piles - working_piles
        
        self.stdout.write(f'充电桩总数: {total_piles}个')
        self.stdout.write(f'工作中: {working_piles}个')
        self.stdout.write(f'可用: {available_piles}个')
        self.stdout.write(f'利用率: {(working_piles/total_piles*100) if total_piles > 0 else 0:.1f}%')
        
        # 请求统计
        total_requests = ChargingRequest.objects.count()
        active_requests = ChargingRequest.objects.filter(
            current_status__in=['waiting', 'charging']
        ).count()
        completed_requests = ChargingRequest.objects.filter(
            current_status='completed'
        ).count()
        cancelled_requests = ChargingRequest.objects.filter(
            current_status='cancelled'
        ).count()
        
        self.stdout.write(f'\n请求统计:')
        self.stdout.write(f'   总请求数: {total_requests}')
        self.stdout.write(f'   活跃请求: {active_requests}')
        self.stdout.write(f'   已完成: {completed_requests}')
        self.stdout.write(f'   已取消: {cancelled_requests}')
        
        # 今日统计
        today = timezone.now().date()
        today_requests = ChargingRequest.objects.filter(
            created_at__date=today
        ).count()
        today_completed = ChargingRequest.objects.filter(
            created_at__date=today,
            current_status='completed'
        ).count()
        
        self.stdout.write(f'\n今日统计:')
        self.stdout.write(f'   今日请求: {today_requests}')
        self.stdout.write(f'   今日完成: {today_completed}')
        
        # 参数配置状态
        param_count = SystemParameter.objects.count()
        editable_param_count = SystemParameter.objects.filter(is_editable=True).count()
        
        self.stdout.write(f'\n参数配置:')
        self.stdout.write(f'   总参数数: {param_count}')
        self.stdout.write(f'   可编辑参数: {editable_param_count}')
        
        self.stdout.write(f'\n⏰ 查询时间: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}') 