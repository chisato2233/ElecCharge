from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Vehicle

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ['id', 'license_plate', 'battery_capacity', 'vehicle_model', 'is_default', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate_license_plate(self, value):
        # 检查车牌号是否已被当前用户注册
        user = self.context['request'].user
        if Vehicle.objects.filter(user=user, license_plate=value).exists():
            raise serializers.ValidationError("您已经注册过这个车牌号")
        return value

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])    
    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'phone']
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
        # 只创建用户，不创建车辆信息
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            phone=validated_data.get('phone', '')
        )
        
        return user

class VehicleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ['license_plate', 'battery_capacity', 'vehicle_model', 'is_default']
    
    def validate_license_plate(self, value):
        # 检查车牌号是否已被当前用户注册
        user = self.context['request'].user
        if Vehicle.objects.filter(user=user, license_plate=value).exists():
            raise serializers.ValidationError("您已经注册过这个车牌号")
        return value
    
    def create(self, validated_data):
        user = self.context['request'].user
        
        # 如果设置为默认车辆，先取消其他车辆的默认状态
        if validated_data.get('is_default', False):
            Vehicle.objects.filter(user=user, is_default=True).update(is_default=False)
        
        # 如果是用户的第一辆车，自动设为默认
        if not Vehicle.objects.filter(user=user).exists():
            validated_data['is_default'] = True
        
        vehicle = Vehicle.objects.create(
            user=user,
            **validated_data
        )
        return vehicle

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
    vehicles = VehicleSerializer(many=True, read_only=True)  # 包含用户的所有车辆
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'is_admin', 'created_at', 'vehicles']
        read_only_fields = ['id', 'created_at']
