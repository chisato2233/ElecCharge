#!/bin/bash
set -e

echo "🔍 检查环境变量..."
if [ -z "$DJANGO_SECRET_KEY" ]; then
    echo "❌ DJANGO_SECRET_KEY 未设置"
    exit 1
fi

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
