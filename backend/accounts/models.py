from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='手机号')
    is_admin = models.BooleanField(default=False, verbose_name='是否为管理员')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'

class Vehicle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    license_plate = models.CharField(max_length=20, unique=True, verbose_name='车牌号')
    battery_capacity = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='电池容量(度)')
    vehicle_model = models.CharField(max_length=100, blank=True, verbose_name='车辆型号')
    is_default = models.BooleanField(default=True, verbose_name='是否为默认车辆')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicles'
        verbose_name = '车辆'
        verbose_name_plural = '车辆'
        
    def __str__(self):
        return f"{self.license_plate} - {self.user.username}"
