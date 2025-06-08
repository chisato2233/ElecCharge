from django.core.management.base import BaseCommand
from django.db import transaction
from charging.models import ChargingPile, SystemParameter, ChargingRequest
from charging.utils.parameter_manager import ParameterManager
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '根据系统参数同步充电桩数据库状态'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制同步，即使存在活跃的充电请求也会继续',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将要执行的操作，不实际修改数据库',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='显示详细信息',
        )

    def handle(self, *args, **options):
        self.verbosity = options['verbosity']
        self.force = options.get('force', False)
        self.dry_run = options.get('dry_run', False)
        self.verbose = options.get('verbose', False)
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('🧪 DRY RUN 模式 - 不会实际修改数据库'))
        
        self.stdout.write(self.style.SUCCESS('🔄 开始同步充电桩状态...'))
        self.stdout.write('=' * 60)
        
        try:
            # 检查系统参数
            if not self._check_system_parameters():
                return
            
            # 获取当前配置
            config = self._get_charging_pile_config()
            if not config:
                return
            
            # 显示当前状态
            self._show_current_status()
            
            # 检查是否有活跃请求
            if not self.force and not self._check_active_requests():
                return
            
            # 执行同步
            if not self.dry_run:
                with transaction.atomic():
                    self._sync_charging_piles(config)
            else:
                self._preview_sync_operations(config)
            
            # 显示同步后状态
            if not self.dry_run:
                self.stdout.write('\n' + '=' * 60)
                self.stdout.write(self.style.SUCCESS('✅ 同步完成！'))
                self._show_current_status()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 同步过程中发生错误: {e}')
            )
            logger.error(f"充电桩同步失败: {e}", exc_info=True)

    def _check_system_parameters(self):
        """检查必需的系统参数是否存在"""
        self.stdout.write('🔍 检查系统参数...')
        
        required_params = [
            'fast_charging_pile_num',
            'slow_charging_pile_num', 
            'fast_charging_power',
            'slow_charging_power',
            'fast_pile_max_queue_size',
            'slow_pile_max_queue_size'
        ]
        
        missing_params = []
        for param in required_params:
            try:
                SystemParameter.objects.get(param_key=param)
                if self.verbose:
                    self.stdout.write(f'   ✓ {param}')
            except SystemParameter.DoesNotExist:
                missing_params.append(param)
                self.stdout.write(f'   ❌ {param} - 缺失')
        
        if missing_params:
            self.stdout.write(
                self.style.ERROR(f'❌ 缺少必需的系统参数: {missing_params}')
            )
            self.stdout.write('请先运行: python manage.py reset_system_parameters')
            return False
        
        self.stdout.write('✅ 系统参数检查完成')
        return True

    def _get_charging_pile_config(self):
        """获取充电桩配置参数"""
        try:
            config = {
                'fast_pile_num': ParameterManager.get_parameter('fast_charging_pile_num', 2, 'int'),
                'slow_pile_num': ParameterManager.get_parameter('slow_charging_pile_num', 5, 'int'),
                'fast_power': ParameterManager.get_parameter('fast_charging_power', 120.0, 'float'),
                'slow_power': ParameterManager.get_parameter('slow_charging_power', 7.0, 'float'),
                'fast_queue_size': ParameterManager.get_parameter('fast_pile_max_queue_size', 3, 'int'),
                'slow_queue_size': ParameterManager.get_parameter('slow_pile_max_queue_size', 5, 'int'),
            }
            
            if self.verbose:
                self.stdout.write('\n📋 当前配置参数:')
                self.stdout.write(f'   快充桩数量: {config["fast_pile_num"]}个')
                self.stdout.write(f'   慢充桩数量: {config["slow_pile_num"]}个')
                self.stdout.write(f'   快充桩功率: {config["fast_power"]}kW')
                self.stdout.write(f'   慢充桩功率: {config["slow_power"]}kW')
                self.stdout.write(f'   快充桩队列容量: {config["fast_queue_size"]}人')
                self.stdout.write(f'   慢充桩队列容量: {config["slow_queue_size"]}人')
            
            return config
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 获取配置参数失败: {e}')
            )
            return None

    def _show_current_status(self):
        """显示当前充电桩状态"""
        self.stdout.write('\n📊 当前充电桩状态:')
        
        fast_piles = ChargingPile.objects.filter(pile_type='fast')
        slow_piles = ChargingPile.objects.filter(pile_type='slow')
        
        def show_pile_stats(piles, pile_type_name):
            if not piles.exists():
                self.stdout.write(f'   {pile_type_name}: 无')
                return
                
            total = piles.count()
            normal = piles.filter(status='normal').count()
            fault = piles.filter(status='fault').count()
            offline = piles.filter(status='offline').count()
            working = piles.filter(is_working=True).count()
            
            self.stdout.write(f'   {pile_type_name}: {total}个')
            self.stdout.write(f'     └─ 正常: {normal}, 故障: {fault}, 离线: {offline}, 工作中: {working}')
            
            if self.verbose:
                for pile in piles:
                    queue_count = pile.get_queue_count()
                    status_icon = '🟢' if pile.status == 'normal' else ('🔴' if pile.status == 'fault' else '⚪')
                    work_icon = '⚡' if pile.is_working else '💤'
                    self.stdout.write(
                        f'       {status_icon}{work_icon} {pile.pile_id}: '
                        f'{pile.charging_power}kW, 队列{queue_count}/{pile.max_queue_size}'
                    )
        
        show_pile_stats(fast_piles, '快充桩')
        show_pile_stats(slow_piles, '慢充桩')

    def _check_active_requests(self):
        """检查是否有活跃的充电请求"""
        active_requests = ChargingRequest.objects.filter(
            current_status__in=['waiting', 'charging']
        ).count()
        
        if active_requests > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠️  发现 {active_requests} 个活跃的充电请求')
            )
            
            if not self.force:
                self.stdout.write(
                    self.style.ERROR('❌ 为避免影响用户服务，同步已终止')
                )
                self.stdout.write('如需强制同步，请使用 --force 参数')
                return False
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  使用 --force 参数，将继续同步')
                )
        
        return True

    def _preview_sync_operations(self, config):
        """预览将要执行的同步操作"""
        self.stdout.write('\n🔍 预览同步操作:')
        
        # 快充桩操作预览
        self._preview_pile_operations('fast', config['fast_pile_num'], 
                                    config['fast_power'], config['fast_queue_size'])
        
        # 慢充桩操作预览
        self._preview_pile_operations('slow', config['slow_pile_num'], 
                                    config['slow_power'], config['slow_queue_size'])

    def _preview_pile_operations(self, pile_type, target_count, target_power, target_queue_size):
        """预览特定类型桩的操作"""
        type_name = '快充桩' if pile_type == 'fast' else '慢充桩'
        current_piles = ChargingPile.objects.filter(pile_type=pile_type)
        current_count = current_piles.count()
        
        self.stdout.write(f'\n   📌 {type_name}:')
        
        # 数量变化
        if target_count > current_count:
            add_count = target_count - current_count
            self.stdout.write(f'     ➕ 将添加 {add_count} 个{type_name}')
            # 显示将要创建的桩ID
            for i in range(current_count + 1, target_count + 1):
                pile_id = f'{"FAST" if pile_type == "fast" else "SLOW"}-{i:03d}'
                self.stdout.write(f'        - {pile_id}')
        elif target_count < current_count:
            remove_count = current_count - target_count
            # 找出将要删除的桩
            removable_piles = current_piles.filter(is_working=False).order_by('-pile_id')[:remove_count]
            if removable_piles.count() >= remove_count:
                self.stdout.write(f'     ➖ 将删除 {remove_count} 个未使用的{type_name}')
                for pile in removable_piles:
                    self.stdout.write(f'        - {pile.pile_id}')
            else:
                self.stdout.write(f'     ⚠️  需要删除 {remove_count} 个{type_name}，但只有 {removable_piles.count()} 个未使用')
        else:
            self.stdout.write(f'     ✓ {type_name}数量无需变化 ({current_count}个)')
        
        # 参数更新
        need_power_update = current_piles.exclude(charging_power=target_power).exists()
        need_queue_update = current_piles.exclude(max_queue_size=target_queue_size).exists()
        
        if need_power_update:
            self.stdout.write(f'     🔧 将更新充电功率为 {target_power}kW')
        if need_queue_update:
            self.stdout.write(f'     🔧 将更新队列容量为 {target_queue_size}人')
        
        if not need_power_update and not need_queue_update:
            self.stdout.write(f'     ✓ {type_name}参数无需更新')

    def _sync_charging_piles(self, config):
        """执行充电桩同步"""
        self.stdout.write('\n🔄 执行同步操作:')
        
        # 同步快充桩
        fast_result = self._sync_piles_by_type('fast', config['fast_pile_num'], 
                                             config['fast_power'], config['fast_queue_size'])
        
        # 同步慢充桩
        slow_result = self._sync_piles_by_type('slow', config['slow_pile_num'], 
                                             config['slow_power'], config['slow_queue_size'])
        
        # 汇总结果
        total_added = fast_result['added'] + slow_result['added']
        total_removed = fast_result['removed'] + slow_result['removed']
        total_updated = fast_result['updated'] + slow_result['updated']
        
        self.stdout.write(f'\n📈 同步结果汇总:')
        self.stdout.write(f'   ➕ 新增充电桩: {total_added}个')
        self.stdout.write(f'   ➖ 删除充电桩: {total_removed}个')
        self.stdout.write(f'   🔧 更新充电桩: {total_updated}个')

    def _sync_piles_by_type(self, pile_type, target_count, target_power, target_queue_size):
        """同步特定类型的充电桩"""
        type_name = '快充桩' if pile_type == 'fast' else '慢充桩'
        type_prefix = 'FAST' if pile_type == 'fast' else 'SLOW'
        
        current_piles = ChargingPile.objects.filter(pile_type=pile_type)
        current_count = current_piles.count()
        
        added = 0
        removed = 0
        updated = 0
        
        self.stdout.write(f'\n   🔧 同步{type_name}:')
        
        # 1. 调整数量
        if target_count > current_count:
            # 需要增加充电桩
            add_count = target_count - current_count
            for i in range(current_count + 1, target_count + 1):
                pile_id = f'{type_prefix}-{i:03d}'
                ChargingPile.objects.create(
                    pile_id=pile_id,
                    pile_type=pile_type,
                    status='normal',
                    charging_power=target_power,
                    max_queue_size=target_queue_size
                )
                added += 1
                self.stdout.write(f'     ➕ 创建: {pile_id}')
                
        elif target_count < current_count:
            # 需要减少充电桩
            remove_count = current_count - target_count
            removable_piles = current_piles.filter(
                is_working=False
            ).order_by('-pile_id')[:remove_count]
            
            if removable_piles.count() < remove_count:
                self.stdout.write(
                    self.style.WARNING(
                        f'     ⚠️  只能删除 {removable_piles.count()} 个未使用的{type_name}，'
                        f'需要删除 {remove_count} 个'
                    )
                )
            
            for pile in removable_piles:
                pile_id = pile.pile_id
                pile.delete()
                removed += 1
                self.stdout.write(f'     ➖ 删除: {pile_id}')
        
        # 2. 更新现有充电桩的参数
        remaining_piles = ChargingPile.objects.filter(pile_type=pile_type)
        for pile in remaining_piles:
            need_update = False
            update_fields = []
            
            if pile.charging_power != target_power:
                pile.charging_power = target_power
                update_fields.append('charging_power')
                need_update = True
            
            if pile.max_queue_size != target_queue_size:
                pile.max_queue_size = target_queue_size
                update_fields.append('max_queue_size')
                need_update = True
            
            if need_update:
                pile.save(update_fields=update_fields)
                updated += 1
                self.stdout.write(f'     🔧 更新: {pile.pile_id} - {", ".join(update_fields)}')
        
        return {'added': added, 'removed': removed, 'updated': updated}

    def _generate_pile_id(self, pile_type, index):
        """生成标准化的充电桩ID"""
        prefix = 'FAST' if pile_type == 'fast' else 'SLOW'
        return f'{prefix}-{index:03d}' 