#!/bin/bash
set -e

echo "🔍 检查环境变量..."
if [ -z "$DJANGO_SECRET_KEY" ]; then
    echo "❌ DJANGO_SECRET_KEY 未设置"
    exit 1
fi


# 显示关键环境变量
echo "📊 当前环境配置:"
echo "   DEBUG: $DEBUG"
echo "   DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:0:10}..."
echo "   DB_HOST: $DB_HOST"
echo "   DB_PORT: $DB_PORT"

# 如果.env文件存在，则加载它
if [ -f .env ]; then
    echo "📄 发现.env文件，正在加载..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# 验证Django设置
echo "🔧 验证Django配置..."
python manage.py shell -c "
from django.conf import settings
print(f'🐛 DEBUG模式: {settings.DEBUG}')
print(f'🔑 SECRET_KEY: {settings.SECRET_KEY[:10]}...')
print(f'🗄️  数据库: {settings.DATABASES[\"default\"][\"ENGINE\"]}')
print(f'🌐 ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}')
if hasattr(settings, 'CORS_ALLOWED_ORIGINS'):
    print(f'🔗 CORS_ALLOWED_ORIGINS: {settings.CORS_ALLOWED_ORIGINS}')
"

echo "⏳ 等待数据库连接..."
while ! nc -z $DB_HOST $DB_PORT; do
    echo "等待数据库 $DB_HOST:$DB_PORT..."
    sleep 2
done
echo "✅ 数据库已连接"

echo "📦 收集静态文件..."
python manage.py collectstatic --noinput

echo "🔄 创建迁移文件..."
python manage.py makemigrations accounts
python manage.py makemigrations

echo "🔄 执行数据库迁移..."
python manage.py migrate

echo "🔄 初始化系统参数..."
python manage.py init_system

echo "👤 创建超级用户(如果不存在)..."
python manage.py shell -c "
from accounts.models import User;
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', '123456')
    print('超级用户已创建: admin/123456')
else:
    print('超级用户已存在')
"

echo "🚀 启动Django服务器..."
echo "📱 访问地址:"
echo "   - 系统首页: http://localhost:8000/"
echo "   - API首页: http://localhost:8000/api/"
echo "   - 健康检查: http://localhost:8000/health/"
echo "   - 管理后台: http://localhost:8000/admin/"

exec gunicorn ev_charge.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
