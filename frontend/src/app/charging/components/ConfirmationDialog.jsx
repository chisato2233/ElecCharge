'use client';

import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { CheckCircle, Info, Clock, DollarSign } from 'lucide-react';
import { 
  estimateChargingRequest, 
  formatTimeEstimate, 
  formatCurrency 
} from '@/lib/chargingEstimator';

export default function ConfirmationDialog({
  open,
  onOpenChange,
  requestData,
  vehicles,
  systemParams,
  queueStatus,
  submitting,
  onConfirm
}) {
  if (!requestData) return null;

  const vehicle = vehicles.find(v => v.id.toString() === requestData.vehicle_id);
  
  // 计算精确估算
  const estimation = estimateChargingRequest(
    {
      charging_mode: requestData.charging_mode,
      requested_amount: parseFloat(requestData.requested_amount),
      start_time: new Date()
    },
    systemParams,
    queueStatus
  );

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center">
            <CheckCircle className="mr-2 h-5 w-5 text-green-600" />
            确认充电请求
          </AlertDialogTitle>
          <AlertDialogDescription>
            请确认您的充电请求信息，提交后将为您智能分配充电桩
          </AlertDialogDescription>
        </AlertDialogHeader>
        
        <div className="space-y-4">
          {/* 基本信息 */}
          <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">车辆：</span>
              <span className="font-semibold">{vehicle?.license_plate}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">充电模式：</span>
              <span className="font-semibold">
                {requestData.charging_mode === 'fast' ? '快充' : '慢充'}
                {estimation?.charging_power && ` (${estimation.charging_power}kW)`}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">充电量：</span>
              <span className="font-semibold">{requestData.requested_amount} kWh</span>
            </div>
          </div>
          
          {/* 精确估算信息 */}
          {estimation && !estimation.error ? (
            <div className="space-y-3">
              {/* 时间估算 */}
              <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                <div className="flex items-center mb-2">
                  <Clock className="w-4 h-4 text-blue-600 mr-2" />
                  <span className="font-medium text-blue-900 dark:text-blue-100">时间估算</span>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-blue-700 dark:text-blue-300">等待时间：</span>
                    <span className="font-semibold">{estimation.summary.wait_time_display}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-blue-700 dark:text-blue-300">充电时间：</span>
                    <span className="font-semibold">{estimation.summary.charging_time_display}</span>
                  </div>
                  <div className="flex justify-between border-t pt-2">
                    <span className="text-blue-700 dark:text-blue-300 font-medium">总用时：</span>
                    <span className="font-bold text-blue-600">{estimation.summary.total_time_display}</span>
                  </div>
                  {estimation.wait_time?.queue_position && (
                    <div className="text-xs text-blue-600 dark:text-blue-400 mt-2">
                      排队位置：第 {estimation.wait_time.queue_position} 位
                      {estimation.wait_time.ahead_count > 0 && 
                        ` (前方 ${estimation.wait_time.ahead_count} 人等待)`
                      }
                    </div>
                  )}
                </div>
              </div>
              
              {/* 费用估算 */}
              <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
                <div className="flex items-center mb-2">
                  <DollarSign className="w-4 h-4 text-green-600 mr-2" />
                  <span className="font-medium text-green-900 dark:text-green-100">费用估算</span>
                </div>
                <div className="space-y-2 text-sm">
                  {estimation.cost_breakdown && (
                    <>
                      {estimation.cost_breakdown.peak_cost > 0 && (
                        <div className="flex justify-between">
                          <span className="text-red-600">峰时电费：</span>
                          <span>{formatCurrency(estimation.cost_breakdown.peak_cost)}</span>
                        </div>
                      )}
                      {estimation.cost_breakdown.normal_cost > 0 && (
                        <div className="flex justify-between">
                          <span className="text-yellow-600">平时电费：</span>
                          <span>{formatCurrency(estimation.cost_breakdown.normal_cost)}</span>
                        </div>
                      )}
                      {estimation.cost_breakdown.valley_cost > 0 && (
                        <div className="flex justify-between">
                          <span className="text-green-600">谷时电费：</span>
                          <span>{formatCurrency(estimation.cost_breakdown.valley_cost)}</span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="text-blue-600">服务费：</span>
                        <span>{formatCurrency(estimation.cost_breakdown.service_cost)}</span>
                      </div>
                    </>
                  )}
                  <div className="flex justify-between border-t pt-2">
                    <span className="text-green-700 dark:text-green-300 font-medium">总费用：</span>
                    <span className="font-bold text-green-600 text-lg">
                      {formatCurrency(estimation.summary.total_cost)}
                    </span>
                  </div>
                </div>
              </div>

              {/* 预计充电时间段 */}
              {estimation.estimated_start_time && estimation.estimated_end_time && (
                <div className="bg-amber-50 dark:bg-amber-900/20 p-4 rounded-lg">
                  <div className="flex items-center mb-2">
                    <Info className="w-4 h-4 text-amber-600 mr-2" />
                    <span className="font-medium text-amber-900 dark:text-amber-100">预计充电时段</span>
                  </div>
                  <div className="text-sm text-amber-700 dark:text-amber-300">
                    <div>开始时间：{estimation.estimated_start_time.toLocaleString()}</div>
                    <div>结束时间：{estimation.estimated_end_time.toLocaleString()}</div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg text-center">
              <span className="text-gray-500 dark:text-gray-400">
                {estimation?.error || '正在计算估算信息...'}
              </span>
            </div>
          )}
          
          <div className="text-sm text-gray-600 dark:text-gray-400 bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
            <div className="flex items-start">
              <Info className="w-4 h-4 text-blue-500 mt-0.5 mr-2 flex-shrink-0" />
              <div>
                <div className="font-medium mb-1">温馨提示</div>
                <div className="text-xs">
                  • 实际充电时间和费用可能因系统状态变化而有所差异<br/>
                  • 提交后请保持车辆准备状态，我们会及时通知您<br/>
                  • 可在充电状态页面实时查看排队进度
                </div>
              </div>
            </div>
          </div>
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={submitting}>取消</AlertDialogCancel>
          <AlertDialogAction 
            onClick={onConfirm} 
            disabled={submitting}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {submitting ? '提交中...' : '确认提交'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
} 