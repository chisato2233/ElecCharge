from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from .serializers import UserRegistrationSerializer, UserLoginSerializer, UserSerializer
from .models import User

# Create your views here.

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    用户注册
    POST /api/auth/register
    """
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
                    'token': token.key
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'REGISTRATION_FAILED',
                    'message': '注册失败',
                    'details': str(e)
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
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
    """
    获取用户信息
    GET /api/auth/profile
    """
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
