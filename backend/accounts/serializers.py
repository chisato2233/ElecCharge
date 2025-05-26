from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Vehicle

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ['license_plate', 'battery_capacity', 'vehicle_model']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    vehicle_info = VehicleSerializer(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'phone', 'vehicle_info']
        extra_kwargs = {
            'email': {'required': True},
            'password': {'write_only': True}
        }
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("该邮箱已被注册")
        return value
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("该用户名已被使用")
        return value
    
    def create(self, validated_data):
        vehicle_data = validated_data.pop('vehicle_info')
        
        # 创建用户
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            phone=validated_data.get('phone', '')
        )
        
        # 创建车辆信息
        Vehicle.objects.create(
            user=user,
            license_plate=vehicle_data['license_plate'],
            battery_capacity=vehicle_data['battery_capacity'],
            vehicle_model=vehicle_data.get('vehicle_model', ''),
            is_default=True
        )
        
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError("用户名或密码错误")
            if not user.is_active:
                raise serializers.ValidationError("用户账户已被禁用")
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError("必须提供用户名和密码")

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'is_admin', 'created_at']
        read_only_fields = ['id', 'created_at']
