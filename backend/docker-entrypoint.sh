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

echo "🔄 初始化和重置系统参数..."
# 检查是否已有参数数据，如果没有则自动确认重置
PARAM_COUNT=$(python manage.py shell -c "
from charging.models import SystemParameter
try:
    count = SystemParameter.objects.count()
    print(count)
except Exception:
    print(0)
")

if [ "$PARAM_COUNT" -eq 0 ]; then
    echo "📝 首次部署，自动初始化系统参数..."
    python manage.py reset_system_parameters --confirm
else
    echo "📋 发现已有 $PARAM_COUNT 个系统参数"
    echo "🔍 检查参数系统完整性..."
    
    # 检查是否有新的统一命名参数
    HAS_NEW_PARAMS=$(python manage.py shell -c "
from charging.models import SystemParameter
try:
    # 检查是否有新的统一命名参数
    new_param = SystemParameter.objects.filter(param_key='fast_charging_pile_num').exists()
    old_param = SystemParameter.objects.filter(param_key='FastChargingPileNum').exists()
    print('new' if new_param else ('old' if old_param else 'none'))
except Exception:
    print('none')
")
    
    if [ "$HAS_NEW_PARAMS" = "old" ]; then
        echo "🔄 检测到旧参数格式，执行参数系统升级..."
        python manage.py reset_system_parameters --confirm
    elif [ "$HAS_NEW_PARAMS" = "new" ]; then
        echo "✅ 参数系统已是最新格式"
    else
        echo "⚠️  参数系统异常，重新初始化..."
        python manage.py reset_system_parameters --confirm
    fi
fi

echo "🧪 验证参数管理系统..."
python manage.py test_new_parameters

echo "🔍 检查系统参数完整性..."
python manage.py check_system_parameters --fix --verbose

echo "👤 创建超级用户(如果不存在)..."
python manage.py shell -c "
from accounts.models import User;
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', '123456')
    print('超级用户已创建: admin/123456')
else:
    print('超级用户已存在')
"

# 创建日志目录
mkdir -p /var/log

# 定义进程PID文件
CHARGING_PID_FILE="/tmp/charging_progress.pid"
GUNICORN_PID_FILE="/tmp/gunicorn.pid"

# 清理函数
cleanup() {
    echo "🛑 接收到停止信号，正在优雅停止服务..."
    
    # 停止充电守护进程
    if [ -f "$CHARGING_PID_FILE" ]; then
        CHARGING_PID=$(cat $CHARGING_PID_FILE)
        if kill -0 $CHARGING_PID 2>/dev/null; then
            echo "⏹️ 停止充电进度守护进程 (PID: $CHARGING_PID)..."
            kill -TERM $CHARGING_PID
            # 等待进程停止
            for i in {1..10}; do
                if ! kill -0 $CHARGING_PID 2>/dev/null; then
                    break
                fi
                sleep 1
            done
            if kill -0 $CHARGING_PID 2>/dev/null; then
                echo "🔥 强制停止充电进程..."
                kill -KILL $CHARGING_PID
            fi
        fi
        rm -f $CHARGING_PID_FILE
    fi
    
    # 停止Gunicorn进程
    if [ -f "$GUNICORN_PID_FILE" ]; then
        GUNICORN_PID=$(cat $GUNICORN_PID_FILE)
        if kill -0 $GUNICORN_PID 2>/dev/null; then
            echo "⏹️ 停止Gunicorn服务 (PID: $GUNICORN_PID)..."
            kill -TERM $GUNICORN_PID
        fi
        rm -f $GUNICORN_PID_FILE
    fi
    
    echo "🔚 所有服务已停止"
    exit 0
}

# 注册信号处理器
trap cleanup SIGTERM SIGINT

echo "⚡ 启动充电进度守护进程（包含故障检测）..."
python manage.py update_charging_progress --daemon --interval 30 --enable-fault-detection > /var/log/charging_progress.log 2>&1 &
CHARGING_PID=$!
echo $CHARGING_PID > $CHARGING_PID_FILE
echo "✅ 充电进度守护进程已启动 (PID: $CHARGING_PID)"
echo "🔍 故障检测功能已启用"

# 验证充电进程是否正常启动
sleep 2
if ! kill -0 $CHARGING_PID 2>/dev/null; then
    echo "❌ 充电进度守护进程启动失败"
    echo "📄 查看日志:"
    tail -20 /var/log/charging_progress.log
    exit 1
fi

echo "🚀 启动Django服务器..."
echo "📱 访问地址:"
echo "   - 系统首页: http://localhost:8000/"
echo "   - API首页: http://localhost:8000/api/"
echo "   - 健康检查: http://localhost:8000/health/"
echo "   - 管理后台: http://localhost:8000/admin/"
echo "📋 服务状态:"
echo "   - 充电进度守护进程: PID $CHARGING_PID"
echo "   - 日志文件: /var/log/charging_progress.log"
echo "   - 参数管理系统: 已启用新版本 v2.0.0"
echo "   - 故障检测系统: 已启用"
echo ""
echo "🧪 故障测试命令:"
echo "   docker exec <container_name> python manage.py simulate_pile_fault FC001 --action fault"
echo "   docker exec <container_name> python manage.py simulate_pile_fault FC001 --action recover"

# 最后显示系统状态
echo "📊 === 系统启动完成状态 ==="
python manage.py show_status

# 启动Gunicorn（前台运行，这样容器不会退出）
gunicorn ev_charge.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --pid $GUNICORN_PID_FILE \
    --access-logfile /var/log/gunicorn_access.log \
    --error-logfile /var/log/gunicorn_error.log \
    --log-level info &

GUNICORN_PID=$!
echo "✅ Gunicorn服务已启动 (PID: $GUNICORN_PID)"

# 等待任意一个进程退出
wait
