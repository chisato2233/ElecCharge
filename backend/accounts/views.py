from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    VehicleSerializer, VehicleCreateSerializer
)
from .models import User, Vehicle

# Create your views here.

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    用户注册 - 只需要基本信息
    POST /api/auth/register/
    """
    print(f"📥 收到注册请求数据: {request.data}")
    
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            user = serializer.save()
            
            # 创建认证token
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'success': True,
                'message': '注册成功',
                'data': {
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'token': token.key
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"❌ 注册异常: {e}")
            return Response({
                'success': False,
                'error': {
                    'code': 'REGISTRATION_FAILED',
                    'message': '注册失败',
                    'details': str(e)
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    print(f"❌ 序列化器验证失败: {serializer.errors}")
    return Response({
        'success': False,
        'error': {
            'code': 'VALIDATION_ERROR',
            'message': '数据验证失败',
            'details': serializer.errors
        }
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    """
    用户登录
    POST /api/auth/login
    """
    serializer = UserLoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # 创建或获取token
        token, created = Token.objects.get_or_create(user=user)
        
        # 登录用户
        login(request, user)
        
        return Response({
            'success': True,
            'message': '登录成功',
            'data': {
                'user_id': user.id,
                'username': user.username,
                'token': token.key,
                'is_admin': user.is_admin
            }
        }, status=status.HTTP_200_OK)
    
    return Response({
        'success': False,
        'error': {
            'code': 'AUTH_INVALID',
            'message': '登录失败',
            'details': serializer.errors
        }
    }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
def user_logout(request):
    """
    用户登出
    POST /api/auth/logout
    """
    try:
        # 删除用户的token
        if hasattr(request.user, 'auth_token'):
            request.user.auth_token.delete()
        
        # 登出用户
        logout(request)
        
        return Response({
            'success': True,
            'message': '登出成功'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': {
                'code': 'LOGOUT_FAILED',
                'message': '登出失败',
                'details': str(e)
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_user_profile(request):
    """获取用户信息（包含车辆列表）"""
    serializer = UserSerializer(request.user)
    return Response({
        'success': True,
        'data': serializer.data
    }, status=status.HTTP_200_OK)

@api_view(['PUT'])
def update_user_profile(request):
    """
    更新用户信息
    PUT /api/auth/profile
    """
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': True,
            'message': '用户信息更新成功',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    return Response({
        'success': False,
        'error': {
            'code': 'VALIDATION_ERROR',
            'message': '数据验证失败',
            'details': serializer.errors
        }
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def vehicle_list(request):
    """
    获取用户车辆列表 / 添加新车辆
    GET /api/auth/vehicles/
    POST /api/auth/vehicles/
    """
    if request.method == 'GET':
        vehicles = Vehicle.objects.filter(user=request.user)
        serializer = VehicleSerializer(vehicles, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    elif request.method == 'POST':
        serializer = VehicleCreateSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            vehicle = serializer.save()
            return Response({
                'success': True,
                'message': '车辆添加成功',
                'data': VehicleSerializer(vehicle).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': '数据验证失败',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def vehicle_detail(request, vehicle_id):
    """
    获取/更新/删除特定车辆
    GET /api/auth/vehicles/{id}/
    PUT /api/auth/vehicles/{id}/
    DELETE /api/auth/vehicles/{id}/
    """
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id, user=request.user)
    except Vehicle.DoesNotExist:
        return Response({
            'success': False,
            'error': '车辆不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = VehicleSerializer(vehicle)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    elif request.method == 'PUT':
        serializer = VehicleSerializer(
            vehicle, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            # 模型的save方法会处理默认车辆逻辑
            vehicle = serializer.save()
            return Response({
                'success': True,
                'message': '车辆信息更新成功',
                'data': VehicleSerializer(vehicle).data
            })
        
        return Response({
            'success': False,
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': '数据验证失败',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # 如果删除的是默认车辆，需要设置新的默认车辆
        if vehicle.is_default:
            other_vehicle = Vehicle.objects.filter(
                user=request.user
            ).exclude(id=vehicle.id).first()
            
            if other_vehicle:
                other_vehicle.is_default = True
                other_vehicle.save()
        
        vehicle.delete()
        return Response({
            'success': True,
            'message': '车辆删除成功'
        })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_default_vehicle(request, vehicle_id):
    """
    设置默认车辆
    POST /api/auth/vehicles/{id}/set-default/
    """
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id, user=request.user)
    except Vehicle.DoesNotExist:
        return Response({
            'success': False,
            'error': '车辆不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # 设置为默认车辆（模型的save方法会自动处理其他车辆的默认状态）
    vehicle.is_default = True
    vehicle.save()
    
    return Response({
        'success': True,
        'message': '默认车辆设置成功',
        'data': VehicleSerializer(vehicle).data
    })
