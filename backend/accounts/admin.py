from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Vehicle

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'phone', 'is_admin', 'is_active', 'created_at']
    list_filter = ['is_admin', 'is_active', 'created_at']
    search_fields = ['username', 'email', 'phone']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('额外信息', {'fields': ('phone', 'is_admin')}),
    )

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['license_plate', 'user', 'battery_capacity', 'vehicle_model', 'is_default', 'created_at']
    list_filter = ['is_default', 'created_at']
    search_fields = ['license_plate', 'user__username', 'vehicle_model']
    raw_id_fields = ['user']
