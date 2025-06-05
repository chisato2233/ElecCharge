#!/bin/bash

# 充电进度守护进程管理脚本

DAEMON_NAME="charging_progress"
PID_FILE="/tmp/charging_progress.pid"
LOG_FILE="/var/log/charging_progress.log"
DJANGO_CMD="python manage.py update_charging_progress --daemon --interval 30"

case "$1" in
    start)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat $PID_FILE)
            if ps -p $PID > /dev/null 2>&1; then
                echo "⚠️ 充电进度守护进程已在运行 (PID: $PID)"
                exit 1
            else
                echo "🧹 清理旧的PID文件..."
                rm -f $PID_FILE
            fi
        fi
        
        echo "🚀 启动充电进度守护进程..."
        nohup $DJANGO_CMD > $LOG_FILE 2>&1 &
        PID=$!
        echo $PID > $PID_FILE
        echo "✅ 充电进度守护进程已启动 (PID: $PID)"
        echo "📋 日志文件: $LOG_FILE"
        ;;
        
    stop)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat $PID_FILE)
            echo "⏹️ 停止充电进度守护进程 (PID: $PID)..."
            kill -TERM $PID 2>/dev/null || true
            
            # 等待进程停止
            for i in {1..10}; do
                if ! ps -p $PID > /dev/null 2>&1; then
                    break
                fi
                sleep 1
            done
            
            if ps -p $PID > /dev/null 2>&1; then
                echo "🔥 强制终止进程..."
                kill -KILL $PID 2>/dev/null || true
            fi
            
            rm -f $PID_FILE
            echo "✅ 充电进度守护进程已停止"
        else
            echo "⚠️ 充电进度守护进程未运行"
        fi
        ;;
        
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat $PID_FILE)
            if ps -p $PID > /dev/null 2>&1; then
                echo "✅ 充电进度守护进程正在运行 (PID: $PID)"
                echo "📋 进程信息:"
                ps -fp $PID
            else
                echo "❌ 充电进度守护进程未运行 (PID文件存在但进程不存在)"
                rm -f $PID_FILE
            fi
        else
            echo "❌ 充电进度守护进程未运行"
        fi
        ;;
        
    log)
        if [ -f "$LOG_FILE" ]; then
            echo "📄 充电进度日志 (最近50行):"
            echo "----------------------------------------"
            tail -50 $LOG_FILE
        else
            echo "❌ 日志文件不存在: $LOG_FILE"
        fi
        ;;
        
    tail)
        if [ -f "$LOG_FILE" ]; then
            echo "📄 实时查看充电进度日志 (按Ctrl+C退出):"
            echo "----------------------------------------"
            tail -f $LOG_FILE
        else
            echo "❌ 日志文件不存在: $LOG_FILE"
        fi
        ;;
        
    *)
        echo "用法: $0 {start|stop|restart|status|log|tail}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动充电进度守护进程"
        echo "  stop    - 停止充电进度守护进程"
        echo "  restart - 重启充电进度守护进程"
        echo "  status  - 查看守护进程状态"
        echo "  log     - 查看最近的日志"
        echo "  tail    - 实时查看日志"
        exit 1
        ;;
esac 