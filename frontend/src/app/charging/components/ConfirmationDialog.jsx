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
import { CheckCircle, Info } from 'lucide-react';

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

export default function ConfirmationDialog({
  open,
  onOpenChange,
  requestData,
  vehicles,
  submitting,
  onConfirm,
  calculateEstimatedCost,
  getQueueWaitTime
}) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center">
            <CheckCircle className="mr-2 h-5 w-5 text-green-600" />
            确认充电请求
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-4">
              <p>请确认以下充电请求信息：</p>
              {requestData && (
                <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">车辆：</span>
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {vehicles.find(v => v.id.toString() === requestData.vehicle_id)?.license_plate}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">充电模式：</span>
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {requestData.charging_mode === 'fast' ? '快充' : '慢充'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">充电量：</span>
                    <span className="font-semibold text-gray-900 dark:text-white">{requestData.requested_amount} kWh</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">预计费用：</span>
                    <span className="font-semibold text-green-600 dark:text-green-400">
                      ¥{calculateEstimatedCost().toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">预计等待：</span>
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {formatTimeEstimate(getQueueWaitTime())}
                    </span>
                  </div>
                </div>
              )}
              <div className="flex items-start space-x-2 text-sm text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 p-3 rounded-lg">
                <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-medium">注意事项：</p>
                  <ul className="list-disc list-inside mt-1 space-y-1">
                    <li>提交后将进入排队等候</li>
                    <li>实际费用以充电结束后结算为准</li>
                    <li>等待期间可以取消请求</li>
                  </ul>
                </div>
              </div>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={submitting}
            className="bg-green-600 hover:bg-green-700"
          >
            {submitting ? '提交中...' : '确认提交'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
} 