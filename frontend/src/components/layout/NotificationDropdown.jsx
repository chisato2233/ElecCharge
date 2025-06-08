'use client';

import { useState, useEffect } from 'react';
import { Bell, Check, CheckCheck, Trash2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuHeader,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { chargingAPI } from '@/lib/charging';
import { useToast } from '@/hooks/use-toast';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

const NotificationIcon = ({ type }) => {
  switch (type) {
    case 'charging_start':
      return '⚡';
    case 'charging_complete':
      return '✅';
    case 'queue_transfer':
      return '🔄';
    case 'pile_fault':
      return '⚠️';
    case 'charging_mode_change':
      return '🔃';
    case 'queue_update':
      return '📊';
    default:
      return '📢';
  }
};

const NotificationDropdown = () => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const { toast } = useToast();

  // 获取通知
  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const response = await chargingAPI.getNotifications();
      if (response.success) {
        setNotifications(response.data);
      }
    } catch (error) {
      console.error('获取通知失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 标记单个通知为已读
  const markAsRead = async (notificationId) => {
    try {
      await chargingAPI.markNotificationRead(notificationId);
      setNotifications(prev => 
        prev.map(notification => 
          notification.id === notificationId 
            ? { ...notification, read: true }
            : notification
        )
      );
    } catch (error) {
      toast({
        title: "操作失败",
        description: "标记通知已读失败",
        variant: "destructive",
      });
    }
  };

  // 标记所有通知为已读
  const markAllAsRead = async () => {
    try {
      const unreadNotifications = notifications.filter(n => !n.read);
      await Promise.all(
        unreadNotifications.map(notification => 
          chargingAPI.markNotificationRead(notification.id)
        )
      );
      setNotifications(prev => 
        prev.map(notification => ({ ...notification, read: true }))
      );
      toast({
        title: "操作成功",
        description: "所有通知已标记为已读",
      });
    } catch (error) {
      toast({
        title: "操作失败", 
        description: "批量标记失败",
        variant: "destructive",
      });
    }
  };

  // 格式化时间
  const formatTime = (timestamp) => {
    try {
      return formatDistanceToNow(new Date(timestamp), {
        addSuffix: true,
        locale: zhCN
      });
    } catch {
      return '刚刚';
    }
  };

  // 组件挂载时获取通知
  useEffect(() => {
    fetchNotifications();
  }, []);

  // 定期刷新通知（每30秒）
  useEffect(() => {
    const interval = setInterval(() => {
      if (!open) { // 只在下拉菜单关闭时自动刷新
        fetchNotifications();
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [open]);

  // 计算未读数量
  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="relative h-8 w-8 rounded-full transition-all duration-200 hover:bg-gray-100 dark:hover:bg-gray-700"
          title="通知"
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <Badge 
              variant="destructive" 
              className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs animate-pulse"
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      
      <DropdownMenuContent 
        align="end" 
        className="w-80 max-h-96"
      >
        {/* 标题栏 */}
        <div className="flex items-center justify-between p-3 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white">
            通知 {unreadCount > 0 && `(${unreadCount})`}
          </h3>
          <div className="flex items-center space-x-1">
            {unreadCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={markAllAsRead}
                className="h-7 px-2 text-xs"
                title="全部标记已读"
              >
                <CheckCheck className="h-3 w-3" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchNotifications}
              className="h-7 px-2 text-xs"
              disabled={loading}
              title="刷新"
            >
              <Bell className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {/* 通知列表 */}
        <div className="max-h-64 overflow-y-auto overflow-x-hidden">
          {loading ? (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-sm">加载中...</p>
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
              <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">暂无通知</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`p-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer ${
                    !notification.read ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                  }`}
                  onClick={() => !notification.read && markAsRead(notification.id)}
                >
                  <div className="flex items-start space-x-3">
                    {/* 通知图标 */}
                    <div className="flex-shrink-0 mt-0.5">
                      <span className="text-lg">
                        <NotificationIcon type={notification.type} />
                      </span>
                    </div>
                    
                    {/* 通知内容 */}
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm ${
                        !notification.read 
                          ? 'font-medium text-gray-900 dark:text-white' 
                          : 'text-gray-700 dark:text-gray-300'
                      }`}>
                        {notification.message}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {formatTime(notification.timestamp)}
                      </p>
                    </div>
                    
                    {/* 未读指示器 */}
                    {!notification.read && (
                      <div className="flex-shrink-0">
                        <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
                      )}
        </div>

        {/* 底部操作栏 */}
        {notifications.length > 0 && (
          <>
            <DropdownMenuSeparator />
            <div className="p-2">
              <Button
                variant="ghost"
                size="sm"
                className="w-full text-center text-xs"
                onClick={() => {
                  setOpen(false);
                  toast({
                    title: "功能提示",
                    description: "通知详情页面正在开发中",
                  });
                }}
              >
                查看所有通知
              </Button>
            </div>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default NotificationDropdown; 