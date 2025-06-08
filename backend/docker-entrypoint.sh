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
# 检查系统参数完整性并自动修复
python manage.py check_system_parameters --fix --verbose

# 检查是否需要重置参数（首次部署或参数不完整）
PARAM_STATUS=$(python manage.py shell -c "
from charging.models import SystemParameter
try:
    # 检查是否有新的统一命名参数
    new_param_count = SystemParameter.objects.filter(param_key__contains='_').count()
    old_param_count = SystemParameter.objects.exclude(param_key__contains='_').count()
    total_count = SystemParameter.objects.count()
    
    if total_count == 0:
        print('empty')
    elif new_param_count >= 10:  # 有足够的新格式参数
        print('updated')
    elif old_param_count > 0:  # 有旧格式参数
        print('old_format')
    else:
        print('incomplete')
except Exception:
    print('error')
")
    
case "$PARAM_STATUS" in
    "empty")
        echo "📝 首次部署，初始化系统参数..."
        python manage.py reset_system_parameters --confirm
        ;;
    "old_format")
        echo "🔄 检测到旧参数格式，升级参数系统..."
        python manage.py reset_system_parameters --confirm
        ;;
    "incomplete")
        echo "⚠️  参数系统不完整，重新初始化..."
        python manage.py reset_system_parameters --confirm
        ;;
    "updated")
        echo "✅ 参数系统已是最新格式"
        ;;
    *)
        echo "❌ 参数系统检查异常，重新初始化..."
        python manage.py reset_system_parameters --confirm
        ;;
esac

echo "🔧 同步充电桩状态..."
# 手动执行充电桩同步（Docker环境下确保同步）
python manage.py sync_charging_piles --verbosity=1

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
echo "   - 参数管理系统: 新版本 v2.0.0 (统一命名)"
echo "   - 充电桩同步: 已完成，运行时自动同步"
echo "   - 故障检测系统: 已启用"
echo ""
echo "🧪 故障测试命令:"
echo "   docker exec <container_name> python manage.py simulate_pile_fault FAST-001 --action fault"
echo "   docker exec <container_name> python manage.py simulate_pile_fault FAST-001 --action recover"
echo ""
echo "🔧 管理命令:"
echo "   docker exec <container_name> python manage.py sync_charging_piles --dry-run"
echo "   docker exec <container_name> python manage.py show_status"
echo "   docker exec <container_name> python manage.py reset_system_parameters --confirm"

# 最后显示系统状态
echo ""
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
