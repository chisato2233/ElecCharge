'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Zap, Car, Clock, MapPin } from 'lucide-react';
import { chargingAPI } from '@/lib/charging';
import { toast } from 'sonner';

// 状态辅助函数
const getStatusVariant = (status) => {
  switch (status) {
    case 'charging': return 'default';
    case 'waiting': return 'secondary';
    case 'completed': return 'outline';
    case 'cancelled': return 'destructive';
    default: return 'outline';
  }
};

const getStatusText = (status) => {
  switch (status) {
    case 'charging': return '充电中';
    case 'waiting': return '等待中';
    case 'completed': return '已完成';
    case 'cancelled': return '已取消';
    default: return '未知';
  }
};

// 队列层级状态显示
const getQueueLevelInfo = (queueLevel, queueStatus) => {
  switch (queueLevel) {
    case 'external_waiting':
      return {
        text: '外部等候区',
        variant: 'outline',
        icon: <Clock className="h-3 w-3 mr-1" />,
        description: '等待分配到充电桩队列'
      };
    case 'pile_queue':
      return {
        text: '桩队列',
        variant: 'secondary',
        icon: <MapPin className="h-3 w-3 mr-1" />,
        description: '已分配充电桩，排队等待'
      };
    case 'charging':
      return {
        text: '正在充电',
        variant: 'default',
        icon: <Zap className="h-3 w-3 mr-1" />,
        description: '正在充电桩充电'
      };
    default:
      return {
        text: queueStatus || '未知',
        variant: 'outline',
        icon: null,
        description: ''
      };
  }
};

// 时间格式化函数
const formatTimeEstimate = (minutes) => {
  if (minutes < 60) {
    return `约 ${minutes} 分钟`;
  } else if (minutes < 120) {
    const remainingMinutes = minutes % 60;
    if (remainingMinutes === 0) {
      return `约 1 小时`;
    } else {
      return `约 1 小时 ${remainingMinutes} 分钟`;
    }
  } else {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    if (remainingMinutes === 0) {
      return `约 ${hours} 小时`;
    } else {
      return `约 ${hours} 小时 ${remainingMinutes} 分钟`;
    }
  }
};

// 单个充电请求卡片
function SingleRequestCard({ request, onRequestUpdate }) {
  const handleCancelRequest = async () => {
    try {
      const response = await chargingAPI.cancelRequest(request.id);
      if (response.success) {
        toast.success('充电请求已取消');
        onRequestUpdate();
      }
    } catch (error) {
      console.error('取消请求失败:', error);
      toast.error('取消请求失败');
    }
  };

  const handleCompleteCharging = async () => {
    try {
      const response = await chargingAPI.completeCharging(request.id);
      if (response.success) {
        toast.success('充电已结束');
        onRequestUpdate();
      }
    } catch (error) {
      console.error('结束充电失败:', error);
      const errorMessage = error.response?.data?.error?.message || '结束充电失败';
      toast.error(errorMessage);
    }
  };

  const handleChangeChargingMode = async () => {
    try {
      const newMode = request.charging_mode === 'fast' ? 'slow' : 'fast';
      const modeText = newMode === 'fast' ? '快充' : '慢充';
      
      const response = await chargingAPI.changeChargingMode(request.id, newMode);
      if (response.success) {
        toast.success(`充电类型已修改为${modeText}，新排队号：${response.data.queue_number}`);
        onRequestUpdate();
      }
    } catch (error) {
      console.error('修改充电类型失败:', error);
      const errorMessage = error.response?.data?.error?.message || '修改充电类型失败';
      toast.error(errorMessage);
    }
  };

  const queueLevelInfo = getQueueLevelInfo(request.queue_level, request.queue_status);

  return (
    <Card className="mb-4">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center">
            <Zap className="mr-2 h-5 w-5" />
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {request.queue_number}
              </h3>
              <div className="flex items-center mt-1 text-sm text-gray-600 dark:text-gray-400">
                <Car className="mr-1 h-3 w-3" />
                <span>{request.vehicle_info?.license_plate || '未知车辆'}</span>
                <span className="mx-2">•</span>
                <span>{request.charging_mode === 'fast' ? '快充' : '慢充'}模式</span>
              </div>
            </div>
          </div>
          <div className="flex flex-col items-end space-y-1">
            <Badge variant={getStatusVariant(request.current_status)}>
              {getStatusText(request.current_status)}
            </Badge>
            {request.queue_level && (
              <Badge variant={queueLevelInfo.variant} className="text-xs">
                {queueLevelInfo.icon}
                {queueLevelInfo.text}
              </Badge>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">请求电量：</span>
              <span className="font-semibold text-gray-900 dark:text-white">{request.requested_amount} kWh</span>
            </div>
            
            {/* 显示队列状态信息 */}
            {request.queue_status && request.queue_level !== 'charging' && (
              <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
                <div className="text-sm text-blue-800 dark:text-blue-200">
                  <div className="font-medium flex items-center">
                    {queueLevelInfo.icon}
                    {request.queue_status}
                  </div>
                  {queueLevelInfo.description && (
                    <div className="text-xs mt-1 text-blue-600 dark:text-blue-300">
                      {queueLevelInfo.description}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          
          <div className="space-y-4">
            {request.current_status === 'waiting' && (
              <>
                {request.queue_level === 'external_waiting' && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">外部等候区位置：</span>
                      <span className="font-semibold text-gray-900 dark:text-white">第 {request.external_queue_position || 'N/A'} 位</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">前方等待：</span>
                      <span className="font-semibold text-gray-900 dark:text-white">{request.ahead_count || 0} 人</span>
                    </div>
                  </>
                )}
                
                {request.queue_level === 'pile_queue' && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">充电桩：</span>
                      <span className="font-semibold text-gray-900 dark:text-white">{request.charging_pile || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">桩队列位置：</span>
                      <span className="font-semibold text-gray-900 dark:text-white">第 {request.pile_queue_position || 'N/A'} 位</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">前方等待：</span>
                      <span className="font-semibold text-gray-900 dark:text-white">{request.ahead_count || 0} 人</span>
                    </div>
                  </>
                )}
                
                {/* 详细时间估算卡片 */}
                {request.time_estimates && (
                  <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg border border-green-200 dark:border-green-800">
                    <div className="flex items-center mb-2">
                      <Clock className="h-4 w-4 text-green-600 dark:text-green-400 mr-2" />
                      <span className="font-semibold text-green-800 dark:text-green-200 text-sm">时间估算</span>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-green-700 dark:text-green-300">预计等待时间：</span>
                        <span className="font-semibold text-green-800 dark:text-green-200">
                          {request.time_estimates.wait_time_display}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-green-700 dark:text-green-300">预计充电时间：</span>
                        <span className="font-semibold text-green-800 dark:text-green-200">
                          {request.time_estimates.charging_time_display}
                        </span>
                      </div>
                      <div className="flex justify-between border-t border-green-200 dark:border-green-700 pt-2">
                        <span className="text-green-700 dark:text-green-300 font-medium">总预计时间：</span>
                        <span className="font-bold text-green-800 dark:text-green-200">
                          {request.time_estimates.total_time_display}
                        </span>
                      </div>
                      {request.time_estimates.pile_remaining_time && (
                        <div className="flex justify-between text-xs text-green-600 dark:text-green-400">
                          <span>桩剩余时间：</span>
                          <span>{request.time_estimates.pile_remaining_display}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {/* 如果没有详细时间估算，显示基本等待时间 */}
                {!request.time_estimates && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">预计等待：</span>
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {request.estimated_wait_time ? formatTimeEstimate(request.estimated_wait_time) : 'N/A'}
                    </span>
                  </div>
                )}
              </>
            )}
            
            {request.current_status === 'charging' && (
              <>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">充电桩：</span>
                  <span className="font-semibold text-gray-900 dark:text-white">{request.charging_pile}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">已充电量：</span>
                  <span className="font-semibold text-gray-900 dark:text-white">{request.current_amount} kWh</span>
                </div>
                
                {/* 充电中的时间信息 */}
                {request.time_estimates && (
                  <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
                    <div className="flex items-center mb-2">
                      <Zap className="h-4 w-4 text-blue-600 dark:text-blue-400 mr-2" />
                      <span className="font-semibold text-blue-800 dark:text-blue-200 text-sm">充电进度</span>
                    </div>
                    <div className="text-sm text-blue-700 dark:text-blue-300">
                      预计总充电时间：{request.time_estimates.charging_time_display}
                    </div>
                  </div>
                )}
                
                <div className="w-full">
                  <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
                    <span>充电进度</span>
                    <span>{Math.round((request.current_amount / request.requested_amount) * 100)}%</span>
                  </div>
                  <Progress 
                    value={(request.current_amount / request.requested_amount) * 100} 
                    className="w-full"
                  />
                </div>
              </>
            )}
          </div>
        </div>
        
        <div className="mt-6 flex justify-end space-x-3">
          {request.current_status === 'waiting' && (
            <>
              {/* 只有在外部等候区才显示修改充电类型按钮 */}
              {request.queue_level === 'external_waiting' && (
                <Button
                  onClick={handleChangeChargingMode}
                  variant="outline"
                  className="text-blue-600 border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20"
                >
                  改为{request.charging_mode === 'fast' ? '慢充' : '快充'}
                </Button>
              )}
            <Button
              onClick={handleCancelRequest}
              variant="outline"
              className="text-red-600 border-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
            >
              取消请求
            </Button>
            </>
          )}
          
          {request.current_status === 'charging' && (
            <Button
              onClick={handleCompleteCharging}
              className="bg-green-600 hover:bg-green-700"
            >
              结束充电
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// 主组件 - 显示所有活跃的充电请求
export default function ChargingStatusList({ activeRequests, onRequestUpdate }) {
  if (!activeRequests || activeRequests.length === 0) {
    return null;
  }

  return (
    <div className="mb-8">
      <div className="mb-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          当前充电请求 ({activeRequests.length})
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          您的活跃充电请求状态 • 支持多级队列管理
        </p>
      </div>
      
      {activeRequests.map((request) => (
        <SingleRequestCard
          key={request.id}
          request={request}
          onRequestUpdate={onRequestUpdate}
        />
      ))}
    </div>
  );
} 