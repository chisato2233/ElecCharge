from charging.utils.config_manager import get_config

class QueueService:
    
    def can_enter_waiting_area(self):
        """检查是否可以进入等候区"""
        waiting_area_size = get_config('WaitingAreaSize', 6)
        current_waiting = 1 #ChargingRequest.objects.filter(status='waiting').count()
        return current_waiting < waiting_area_size
    
    def get_available_piles(self, charging_mode):
        """获取可用的充电桩"""
        if charging_mode == 'fast':
            pile_count = get_config('FastChargingPileNum', 2)
            pile_ids = [chr(65 + i) for i in range(pile_count)]  # A, B, ...
        else:
            pile_count = get_config('TrickleChargingPileNum', 3)
            fast_count = get_config('FastChargingPileNum', 2)
            pile_ids = [chr(65 + fast_count + i) for i in range(pile_count)]  # C, D, E, ...
        
        return 1 #ChargingPile.objects.filter(
            #id__in=pile_ids,
            #status='normal',
            #is_working=True
        #)
    
    def can_join_pile_queue(self, pile_id):
        """检查是否可以加入充电桩队列"""
        queue_len = get_config('ChargingQueueLen', 2)
        current_queue = 1 #ChargingQueue.objects.filter(pile_id=pile_id).count()
        return current_queue < queue_len
