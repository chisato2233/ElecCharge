# backend/charging/serializers.py
from rest_framework import serializers
from .models import ChargingRequest, ChargingPile, ChargingSession, SystemParameter, Notification

class ChargingRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChargingRequest
        fields = ['id', 'queue_number', 'charging_mode', 'requested_amount', 
                 'battery_capacity', 'current_status', 'queue_position', 
                 'estimated_wait_time', 'charging_pile', 'start_time', 
                 'current_amount', 'created_at']
        read_only_fields = ['id', 'queue_number', 'queue_position', 
                           'estimated_wait_time', 'charging_pile', 'start_time', 
                           'current_amount', 'created_at']

class ChargingRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChargingRequest
        fields = ['charging_mode', 'requested_amount', 'battery_capacity']
    
    def validate_requested_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("请求充电量必须大于0")
        return value
    
    def validate_battery_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("电池容量必须大于0")
        return value

class ChargingPileSerializer(serializers.ModelSerializer):
    current_user = serializers.SerializerMethodField()
    queue = serializers.SerializerMethodField()
    
    class Meta:
        model = ChargingPile
        fields = ['pile_id', 'pile_type', 'status', 'is_working', 
                 'current_user', 'queue', 'total_sessions', 'total_duration', 
                 'total_energy', 'total_revenue']
    
    def get_current_user(self, obj):
        if obj.is_working:
            current_request = ChargingRequest.objects.filter(
                charging_pile=obj, 
                current_status='charging'
            ).first()
            return current_request.user.username if current_request else None
        return None
    
    def get_queue(self, obj):
        queue_requests = ChargingRequest.objects.filter(
            charging_mode=obj.pile_type,
            current_status='waiting'
        ).order_by('queue_position')[:3]  # 显示前3个
        
        return [
            {
                'queue_number': req.queue_number,
                'estimated_completion': req.start_time  # 这里需要计算预计完成时间
            }
            for req in queue_requests
        ]

class ChargingSessionSerializer(serializers.ModelSerializer):
    bill_id = serializers.CharField(source='id', read_only=True)
    generated_time = serializers.DateTimeField(source='created_at', read_only=True)
    pile_id = serializers.CharField(source='pile.pile_id', read_only=True)
    pile = serializers.SerializerMethodField()
    
    class Meta:
        model = ChargingSession
        fields = ['id', 'bill_id', 'generated_time', 'pile_id', 'pile', 'charging_amount',
                 'charging_duration', 'start_time', 'end_time', 'peak_hours',
                 'normal_hours', 'valley_hours', 'peak_cost', 'normal_cost',
                 'valley_cost', 'service_cost', 'total_cost']
    
    def get_pile(self, obj):
        return {
            'pile_id': obj.pile.pile_id,
            'pile_type': obj.pile.pile_type
        }

class SystemParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemParameter
        fields = ['key', 'value', 'description']

class NotificationSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'type', 'message', 'read', 'timestamp']