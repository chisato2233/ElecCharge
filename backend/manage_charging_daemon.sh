#!/bin/bash

# 充电进度守护进程管理脚本（包含故障检测功能）

DAEMON_NAME="charging_progress"
PID_FILE="/tmp/charging_progress.pid"
LOG_FILE="/var/log/charging_progress.log"
DJANGO_CMD="python manage.py update_charging_progress --daemon --interval 30 --enable-fault-detection"

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
        
        echo "🚀 启动充电进度守护进程（包含故障检测）..."
        nohup $DJANGO_CMD > $LOG_FILE 2>&1 &
        PID=$!
        echo $PID > $PID_FILE
        echo "✅ 充电进度守护进程已启动 (PID: $PID)"
        echo "🔍 故障检测功能已启用"
        echo "📋 日志文件: $LOG_FILE"
        echo "💡 使用以下命令查看实时日志: $0 tail"
        ;;
        
    start-no-fault)
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
        
        echo "🚀 启动充电进度守护进程（不包含故障检测）..."
        DJANGO_CMD_NO_FAULT="python manage.py update_charging_progress --daemon --interval 0.2"
        nohup $DJANGO_CMD_NO_FAULT > $LOG_FILE 2>&1 &
        PID=$!
        echo $PID > $PID_FILE
        echo "✅ 充电进度守护进程已启动 (PID: $PID)"
        echo "❌ 故障检测功能已禁用"
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
                echo ""
                echo "📊 最近的日志摘要:"
                if [ -f "$LOG_FILE" ]; then
                    tail -5 $LOG_FILE | grep -E "(故障|恢复|充电完成|启动)" || echo "  (最近无重要事件)"
                fi
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
        
    test-fault)
        if [ -z "$2" ]; then
            echo "❌ 请指定充电桩ID"
            echo "用法: $0 test-fault <pile_id> [auto_recover_seconds]"
            echo "示例: $0 test-fault FC001 60"
            exit 1
        fi
        
        PILE_ID="$2"
        AUTO_RECOVER="$3"
        
        echo "🧪 开始故障测试..."
        if [ -n "$AUTO_RECOVER" ]; then
            python manage.py simulate_pile_fault "$PILE_ID" --action fault --auto-recover "$AUTO_RECOVER"
        else
            python manage.py simulate_pile_fault "$PILE_ID" --action fault
        fi
        ;;
        
    test-recover)
        if [ -z "$2" ]; then
            echo "❌ 请指定充电桩ID"
            echo "用法: $0 test-recover <pile_id>"
            exit 1
        fi
        
        PILE_ID="$2"
        echo "🧪 开始恢复测试..."
        python manage.py simulate_pile_fault "$PILE_ID" --action recover
        ;;
        
    check-faults)
        echo "🔍 手动检查所有故障桩..."
        python manage.py update_charging_progress --check-faults
        ;;
        
    *)
        echo "充电进度守护进程管理工具（增强版 v2.0 - 支持故障检测）"
        echo ""
        echo "用法: $0 {start|start-no-fault|stop|restart|status|log|tail|test-fault|test-recover|check-faults}"
        echo ""
        echo "基本命令:"
        echo "  start           - 启动守护进程（包含故障检测）"
        echo "  start-no-fault  - 启动守护进程（不包含故障检测）"
        echo "  stop            - 停止守护进程"
        echo "  restart         - 重启守护进程"
        echo "  status          - 查看进程状态和运行摘要"
        echo ""
        echo "日志命令:"
        echo "  log             - 查看最近的日志"
        echo "  tail            - 实时查看日志"
        echo ""
        echo "测试命令:"
        echo "  test-fault <pile_id> [auto_recover_sec]  - 模拟充电桩故障"
        echo "  test-recover <pile_id>                   - 模拟充电桩恢复"
        echo "  check-faults                            - 手动检查所有故障桩"
        echo ""
        echo "示例:"
        echo "  $0 start                    # 启动守护进程"
        echo "  $0 test-fault FC001 60      # 模拟FC001故障，60秒后自动恢复"
        echo "  $0 tail                     # 实时查看日志"
        echo ""
        echo "功能特性:"
        echo "  ✅ 充电进度实时更新"
        echo "  🔍 充电桩故障自动检测"
        echo "  🚨 故障时自动停止充电并重新调度"
        echo "  🔄 故障恢复后自动重新分配队列"
        echo "  📱 实时通知用户状态变化"
        exit 1
        ;;
esac 