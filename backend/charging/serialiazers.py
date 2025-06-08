# backend/charging/serializers.py
from rest_framework import serializers
from .models import ChargingRequest, ChargingPile, ChargingSession, SystemParameter, Notification

class ChargingRequestSerializer(serializers.ModelSerializer):
    vehicle_info = serializers.SerializerMethodField()
    queue_info = serializers.SerializerMethodField()
    estimated_charging_time = serializers.SerializerMethodField()
    time_estimates = serializers.SerializerMethodField()
    session_info = serializers.SerializerMethodField()
    pile_info = serializers.SerializerMethodField()
    
    class Meta:
        model = ChargingRequest
        fields = ['id', 'queue_number', 'charging_mode', 'requested_amount', 
                 'battery_capacity', 'current_status', 'queue_level',
                 'external_queue_position', 'pile_queue_position',
                 'estimated_wait_time', 'estimated_charging_time', 'time_estimates',
                 'charging_pile', 'start_time', 'end_time', 'current_amount', 'created_at', 'updated_at',
                 'vehicle', 'vehicle_info', 'queue_info', 'session_info', 'pile_info']
        read_only_fields = ['id', 'queue_number', 'queue_level',
                           'external_queue_position', 'pile_queue_position',
                           'estimated_wait_time', 'estimated_charging_time', 'time_estimates',
                           'charging_pile', 'start_time', 'end_time', 'current_amount', 'created_at', 'updated_at',
                           'vehicle_info', 'queue_info', 'session_info', 'pile_info']
    
    def get_vehicle_info(self, obj):
        if obj.vehicle:
            return {
                'id': obj.vehicle.id,
                'license_plate': obj.vehicle.license_plate,
                'battery_capacity': float(obj.vehicle.battery_capacity),
                'vehicle_model': obj.vehicle.vehicle_model
            }
        return None
    
    def get_estimated_charging_time(self, obj):
        """获取预计充电时间(分钟)"""
        return obj.get_estimated_charging_time()
    
    def get_time_estimates(self, obj):
        """获取详细的时间估算信息"""
        charging_time = obj.get_estimated_charging_time()
        
        estimates = {
            'charging_time_minutes': int(charging_time),
            'charging_time_hours': round(charging_time / 60, 1),
            'wait_time_minutes': obj.estimated_wait_time,
            'wait_time_hours': round(obj.estimated_wait_time / 60, 1),
            'total_time_minutes': int(charging_time + obj.estimated_wait_time),
            'total_time_hours': round((charging_time + obj.estimated_wait_time) / 60, 1)
        }
        
        # 添加友好的显示文本
        def format_time(minutes):
            if minutes < 60:
                return f"{int(minutes)}分钟"
            else:
                hours = int(minutes // 60)
                mins = int(minutes % 60)
                if mins == 0:
                    return f"{hours}小时"
                else:
                    return f"{hours}小时{mins}分钟"
        
        estimates['charging_time_display'] = format_time(charging_time)
        estimates['wait_time_display'] = format_time(obj.estimated_wait_time)
        estimates['total_time_display'] = format_time(charging_time + obj.estimated_wait_time)
        
        # 如果已分配充电桩，添加桩的预计剩余时间
        if obj.charging_pile:
            pile_remaining = obj.charging_pile.calculate_remaining_time()
            estimates['pile_remaining_time'] = pile_remaining
            estimates['pile_remaining_display'] = format_time(pile_remaining)
        
        return estimates
    
    def get_queue_info(self, obj):
        """获取队列状态信息"""
        info = {
            'level': obj.queue_level,
            'position': None,
            'pile_id': None
        }
        
        if obj.queue_level == 'external_waiting':
            info['position'] = obj.external_queue_position
            info['description'] = f'外部等候区第{obj.external_queue_position}位'
        elif obj.queue_level == 'pile_queue':
            info['position'] = obj.pile_queue_position
            info['pile_id'] = obj.charging_pile.pile_id if obj.charging_pile else None
            info['description'] = f'充电桩{info["pile_id"]}队列第{obj.pile_queue_position}位'
        elif obj.queue_level == 'charging':
            info['pile_id'] = obj.charging_pile.pile_id if obj.charging_pile else None
            info['description'] = f'正在充电桩{info["pile_id"]}充电'
        elif obj.queue_level == 'completed':
            info['description'] = '充电已完成'
        
        return info
    
    def get_session_info(self, obj):
        """获取会话信息（费用等）"""
        if hasattr(obj, 'session') and obj.session:
            session = obj.session
            return {
                'id': str(session.id),
                'charging_amount': session.charging_amount,
                'charging_duration': session.charging_duration,
                'peak_cost': float(session.peak_cost),
                'normal_cost': float(session.normal_cost),
                'valley_cost': float(session.valley_cost),
                'service_cost': float(session.service_cost),
                'total_cost': float(session.total_cost),
                'peak_hours': session.peak_hours,
                'normal_hours': session.normal_hours,
                'valley_hours': session.valley_hours,
            }
        return None
    
    def get_pile_info(self, obj):
        """获取充电桩信息"""
        if obj.charging_pile:
            return {
                'pile_id': obj.charging_pile.pile_id,
                'pile_type': obj.charging_pile.pile_type,
                'pile_type_display': '快充' if obj.charging_pile.pile_type == 'fast' else '慢充',
                'charging_power': obj.charging_pile.charging_power,
                'status': obj.charging_pile.status
            }
        return None

class ChargingRequestCreateSerializer(serializers.ModelSerializer):
    vehicle_id = serializers.IntegerField(write_only=True, required=True)
    
    class Meta:
        model = ChargingRequest
        fields = ['charging_mode', 'requested_amount', 'battery_capacity', 'vehicle_id']
    
    def validate_requested_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("请求充电量必须大于0")
        return value
    
    def validate_battery_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("电池容量必须大于0")
        return value
    
    def validate_vehicle_id(self, value):
        from accounts.models import Vehicle
        user = self.context['request'].user
        try:
            vehicle = Vehicle.objects.get(id=value, user=user)
            # 检查是否有活跃的充电请求
            existing_request = ChargingRequest.objects.filter(
                vehicle=vehicle, 
                current_status__in=['waiting', 'charging']
            ).exists()
            
            if existing_request:
                raise serializers.ValidationError("该车辆已有未完成的充电请求")
            return value
        except Vehicle.DoesNotExist:
            raise serializers.ValidationError("车辆不存在或不属于当前用户")
    
    def validate(self, attrs):
        # 确保用户有车辆可用
        from accounts.models import Vehicle
        user = self.context['request'].user
        
        # 检查vehicle_id是否存在且有效
        vehicle_id = attrs.get('vehicle_id')
        if not vehicle_id:
            # 如果没有提供vehicle_id，尝试使用默认车辆
            default_vehicle = Vehicle.objects.filter(
                user=user, 
                is_default=True
            ).first()
            
            if not default_vehicle:
                default_vehicle = Vehicle.objects.filter(user=user).first()
            
            if not default_vehicle:
                raise serializers.ValidationError({"vehicle_id": "您尚未添加任何车辆，请先添加车辆信息"})
            
            attrs['vehicle_id'] = default_vehicle.id
        
        return attrs
    
    def create(self, validated_data):
        from accounts.models import Vehicle
        vehicle_id = validated_data.pop('vehicle_id')
        vehicle = Vehicle.objects.get(id=vehicle_id, user=validated_data['user'])
        validated_data['vehicle'] = vehicle
        return super().create(validated_data)

class ChargingPileSerializer(serializers.ModelSerializer):
    current_user = serializers.SerializerMethodField()
    current_vehicle = serializers.SerializerMethodField()
    queue = serializers.SerializerMethodField()
    queue_count = serializers.SerializerMethodField()
    estimated_remaining_time = serializers.SerializerMethodField()
    
    class Meta:
        model = ChargingPile
        fields = ['pile_id', 'pile_type', 'status', 'is_working', 
                 'current_user', 'current_vehicle', 'queue', 'queue_count',
                 'estimated_remaining_time', 'max_queue_size', 'charging_power',
                 'total_sessions', 'total_duration', 'total_energy', 'total_revenue']
    
    def get_current_user(self, obj):
        if obj.is_working:
            current_request = ChargingRequest.objects.filter(
                charging_pile=obj, 
                current_status='charging'
            ).first()
            return current_request.user.username if current_request else None
        return None
    
    def get_current_vehicle(self, obj):
        if obj.is_working:
            current_request = ChargingRequest.objects.filter(
                charging_pile=obj, 
                current_status='charging'
            ).first()
            if current_request and current_request.vehicle:
                return {
                    'license_plate': current_request.vehicle.license_plate,
                    'vehicle_model': current_request.vehicle.vehicle_model
                }
        return None
    
    def get_queue_count(self, obj):
        """获取当前桩队列数量"""
        return obj.get_queue_count()
    
    def get_estimated_remaining_time(self, obj):
        """获取预计剩余时间"""
        return obj.calculate_remaining_time()
    
    def get_queue(self, obj):
        """获取桩队列信息"""
        queue_requests = ChargingRequest.objects.filter(
            charging_pile=obj,
            queue_level='pile_queue'
        ).order_by('pile_queue_position')[:3]  # 显示前3个
        
        return [
            {
                'queue_number': req.queue_number,
                'vehicle_license': req.vehicle.license_plate if req.vehicle else None,
                'position': req.pile_queue_position,
                'requested_amount': req.requested_amount
            }
            for req in queue_requests
        ]

class ChargingSessionSerializer(serializers.ModelSerializer):
    bill_id = serializers.CharField(source='id', read_only=True)
    generated_time = serializers.DateTimeField(source='created_at', read_only=True)
    pile_id = serializers.CharField(source='pile.pile_id', read_only=True)
    pile = serializers.SerializerMethodField()
    vehicle_info = serializers.SerializerMethodField()
    
    class Meta:
        model = ChargingSession
        fields = ['id', 'bill_id', 'generated_time', 'pile_id', 'pile', 'vehicle_info',
                 'charging_amount', 'charging_duration', 'start_time', 'end_time', 
                 'peak_hours', 'normal_hours', 'valley_hours', 'peak_cost', 
                 'normal_cost', 'valley_cost', 'service_cost', 'total_cost']
    
    def get_pile(self, obj):
        return {
            'pile_id': obj.pile.pile_id,
            'pile_type': obj.pile.pile_type
        }
    
    def get_vehicle_info(self, obj):
        if obj.vehicle:
            return {
                'license_plate': obj.vehicle.license_plate,
                'vehicle_model': obj.vehicle.vehicle_model
            }
        return None

class SystemParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemParameter
        fields = ['param_key', 'param_value', 'description', 'param_type']

class NotificationSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'type', 'message', 'read', 'timestamp']