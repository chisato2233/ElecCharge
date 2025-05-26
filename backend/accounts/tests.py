# backend/accounts/tests.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import User, Vehicle

class AuthAPITestCase(APITestCase):
    
    def test_user_registration(self):
        """测试用户注册"""
        url = reverse('accounts:register')
        data = {
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com',
            'phone': '13800138000',
            'vehicle_info': {
                'license_plate': '京A12345',
                'battery_capacity': 60.0
            }
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('token', response.data['data'])
        
        # 验证用户和车辆是否创建成功
        self.assertTrue(User.objects.filter(username='testuser').exists())
        self.assertTrue(Vehicle.objects.filter(license_plate='京A12345').exists())
    
    def test_user_login(self):
        """测试用户登录"""
        # 先创建用户
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        url = reverse('accounts:login')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('token', response.data['data'])
    
    def test_user_logout(self):
        """测试用户登出"""
        # 创建用户并登录
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=user)
        
        url = reverse('accounts:logout')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])