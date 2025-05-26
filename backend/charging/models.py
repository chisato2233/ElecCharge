from django.db import models

# Create your models here.

class SystemParameter(models.Model):
    PARAM_TYPE_CHOICES = [
        ('int', '整数'),
        ('float', '浮点数'),
        ('string', '字符串'),
        ('boolean', '布尔值'),
        ('json', 'JSON'),
    ]
    
    param_key = models.CharField(max_length=100, unique=True, verbose_name='参数键')
    param_value = models.TextField(verbose_name='参数值')
    param_type = models.CharField(max_length=20, choices=PARAM_TYPE_CHOICES, default='string', verbose_name='参数类型')
    description = models.CharField(max_length=255, blank=True, verbose_name='参数描述')
    is_editable = models.BooleanField(default=True, verbose_name='是否可编辑')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'system_parameters'
        verbose_name = '系统参数'
        verbose_name_plural = '系统参数'
    
    def get_value(self):
        """根据类型返回正确的值"""
        if self.param_type == 'int':
            return int(self.param_value)
        elif self.param_type == 'float':
            return float(self.param_value)
        elif self.param_type == 'boolean':
            return self.param_value.lower() in ('true', '1', 'yes')
        elif self.param_type == 'json':
            import json
            return json.loads(self.param_value)
        return self.param_value
    
    def set_value(self, value):
        """设置值并自动转换为字符串"""
        if self.param_type == 'json':
            import json
            self.param_value = json.dumps(value)
        else:
            self.param_value = str(value)
