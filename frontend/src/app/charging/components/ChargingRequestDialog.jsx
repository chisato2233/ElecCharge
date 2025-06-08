'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Slider } from '@/components/ui/slider';
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
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
import { BgAnimateButton } from '@/components/ui/bg-animate-button';
import { Zap, Car, Clock, DollarSign, Battery, Users, AlertTriangle, Plus } from 'lucide-react';
import { chargingAPI } from '@/lib/charging';
import { toast } from 'sonner';
import { 
  estimateChargingRequest, 
  formatTimeEstimate,
  formatCurrency,
  getOptimalChargingTimeSuggestion 
} from '@/lib/chargingEstimator';

export default function ChargingRequestDialog({ 
  vehicles, 
  systemParams, 
  queueStatus,
  onRequestSubmitted,
  activeRequests 
}) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [requestData, setRequestData] = useState(null);
  const [estimation, setEstimation] = useState(null);
  const [enhancedQueueData, setEnhancedQueueData] = useState(null);

  const form = useForm({
    defaultValues: {
      vehicle_id: '',
      charging_mode: 'fast',
      requested_amount: 50,
      battery_capacity: 75
    }
  });

  const watchedValues = form.watch();

  // 获取增强队列数据
  const fetchEnhancedQueueData = async () => {
    try {
      const response = await chargingAPI.getEnhancedQueueStatus();
      if (response.success) {
        setEnhancedQueueData(response.data);
        return response.data;
      }
    } catch (error) {
      console.error('获取增强队列数据失败:', error);
    }
    return null;
  };

  // 实时更新估算
  useEffect(() => {
    if (watchedValues.requested_amount && watchedValues.charging_mode && systemParams) {
      const updateEstimation = async () => {
        const requestData = {
          charging_mode: watchedValues.charging_mode,
          requested_amount: parseFloat(watchedValues.requested_amount),
          start_time: new Date()
        };
        
        // 首先尝试使用增强队列数据进行精确估算
        let queueDataForEstimation = enhancedQueueData || queueStatus;
        if (!enhancedQueueData) {
          // 如果没有增强数据，尝试获取
          const enhancedData = await fetchEnhancedQueueData();
          if (enhancedData) {
            queueDataForEstimation = enhancedData;
          }
        }
        
        const newEstimation = estimateChargingRequest(requestData, systemParams, queueDataForEstimation);
        setEstimation(newEstimation);
      };
      
      updateEstimation();
    }
  }, [watchedValues.requested_amount, watchedValues.charging_mode, systemParams, queueStatus, enhancedQueueData]);

  // 获取可用车辆（排除已有活跃请求的车辆）
  const getAvailableVehicles = () => {
    return vehicles.filter(vehicle => {
      const hasActiveRequest = activeRequests.some(req => 
        req.vehicle_info?.license_plate === vehicle.license_plate && 
        ['waiting', 'charging'].includes(req.current_status)
      );
      return !hasActiveRequest;
    });
  };

  const handleVehicleChange = (vehicleId) => {
    const vehicle = vehicles.find(v => v.id.toString() === vehicleId);
    if (vehicle) {
      form.setValue('battery_capacity', vehicle.battery_capacity);
      // 建议充电量为电池容量的80%
      const suggestedAmount = Math.round(vehicle.battery_capacity * 0.8);
      form.setValue('requested_amount', suggestedAmount);
    }
  };

  const calculateEstimatedCost = () => {
    if (!systemParams || !watchedValues.requested_amount) return 0;
    
    const { pricing } = systemParams;
    const amount = watchedValues.requested_amount;
    
    // 简化计算：假设均匀分布在各时段
    const peakCost = amount * 0.3 * pricing.peak_rate;
    const normalCost = amount * 0.4 * pricing.normal_rate;
    const valleyCost = amount * 0.3 * pricing.valley_rate;
    const serviceCost = amount * pricing.service_rate;
    
    return peakCost + normalCost + valleyCost + serviceCost;
  };

  const getQueueWaitTime = () => {
    if (!queueStatus) return 0;
    
    const mode = watchedValues.charging_mode;
    // 适配新的数据结构：外部等候区 + 桩队列等待时间
    const externalWaitTime = (queueStatus.external_queue?.total_count || 0) * 15; // 外部等候区平均15分钟
    const pileQueueData = mode === 'fast' ? queueStatus.pile_queues?.fast : queueStatus.pile_queues?.slow;
    const pileWaitTime = (pileQueueData?.waiting_count || 0) * 30; // 桩队列平均30分钟
    
    return externalWaitTime + pileWaitTime;
  };

  const formatTimeEstimate = (minutes) => {
    if (minutes < 60) {
      return `约 ${minutes} 分钟`;
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

  const handleSubmit = (data) => {
    // 验证数据
    if (!data.vehicle_id) {
      toast.error('请选择车辆');
      return;
    }
    
    if (data.requested_amount <= 0) {
      toast.error('请求充电量必须大于0');
      return;
    }

    setRequestData(data);
    setConfirmDialogOpen(true);
  };

  const confirmSubmitRequest = async () => {
    try {
      setSubmitting(true);
      
      const vehicle = vehicles.find(v => v.id.toString() === requestData.vehicle_id);
      const submitData = {
        charging_mode: requestData.charging_mode,
        requested_amount: requestData.requested_amount,
        battery_capacity: vehicle.battery_capacity,
        vehicle_id: parseInt(requestData.vehicle_id)
      };
      
      const response = await chargingAPI.submitRequest(submitData);
      
      if (response.success) {
        toast.success('充电请求提交成功！');
        setConfirmDialogOpen(false);
        setDialogOpen(false);
        form.reset();
        onRequestSubmitted && onRequestSubmitted();
      }
    } catch (error) {
      console.error('提交充电请求失败:', error);
      const errorMessage = error.response?.data?.error?.message || '提交失败';
      toast.error(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const availableVehicles = getAvailableVehicles();
  const selectedVehicle = vehicles.find(v => v.id.toString() === watchedValues.vehicle_id);
  const estimatedCost = calculateEstimatedCost();
  const waitTime = getQueueWaitTime();
  
  // 获取充电时间建议
  const timeSuggestions = getOptimalChargingTimeSuggestion(systemParams?.pricing);

  // 获取充电功率
  const getChargingPower = (mode) => {
    if (!systemParams || !systemParams.charging_power) {
      // 默认值
      return mode === 'fast' ? 120 : 7;
    }
    return mode === 'fast' 
      ? systemParams.charging_power.fast_charging_power || 120
      : systemParams.charging_power.slow_charging_power || 7;
  };

  return (
    <>
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogTrigger asChild>
          <BgAnimateButton 
            size="lg"
            gradient="ocean"
            animation="spin-fast"
            shadow="base"
            rounded="3xl"
            className="transition-transform hover:scale-105 whitespace-nowrap"
          >
            <div className="flex items-center justify-center">
              <Plus className="mr-2 h-5 w-5" />
              <span>充电请求</span>
            </div>
          </BgAnimateButton>
        </DialogTrigger>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center">
              <Zap className="mr-2 h-5 w-5" />
              新建充电请求
            </DialogTitle>
            <DialogDescription>
              选择您的车辆和充电参数，系统将为您智能分配充电桩
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            {/* 车辆选择 */}
            <div className="space-y-2">
              <Label htmlFor="vehicle">选择车辆</Label>
              {availableVehicles.length === 0 ? (
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                  <div className="flex items-center">
                    <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 mr-2" />
                    <p className="text-amber-800 dark:text-amber-200">
                      {vehicles.length === 0 
                        ? '您还没有添加任何车辆，请先前往车辆管理页面添加车辆。'
                        : '您的所有车辆都有活跃的充电请求，请等待当前请求完成。'
                      }
                    </p>
                  </div>
                </div>
              ) : (
                <Select 
                  value={watchedValues.vehicle_id} 
                  onValueChange={(value) => {
                    form.setValue('vehicle_id', value);
                    handleVehicleChange(value);
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择要充电的车辆" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableVehicles.map((vehicle) => (
                      <SelectItem key={vehicle.id} value={vehicle.id.toString()}>
                        <div className="flex items-center justify-between w-full">
                          <span>{vehicle.license_plate}</span>
                          <span className="text-sm text-gray-500 ml-2">
                            {vehicle.vehicle_model} • {vehicle.battery_capacity}kWh
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {selectedVehicle && (
              <>
                {/* 车辆信息卡片 */}
                <Card className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm flex items-center">
                      <Car className="mr-2 h-4 w-4" />
                      车辆信息
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>车牌号码：</span>
                      <span className="font-semibold">{selectedVehicle.license_plate}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>车型：</span>
                      <span>{selectedVehicle.vehicle_model}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>电池容量：</span>
                      <span>{selectedVehicle.battery_capacity} kWh</span>
                    </div>
                  </CardContent>
                </Card>

                {/* 充电参数 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="charging_mode">充电模式</Label>
                    <Select 
                      value={watchedValues.charging_mode} 
                      onValueChange={(value) => form.setValue('charging_mode', value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="fast">
                          <div className="flex items-center">
                            <Zap className="mr-2 h-4 w-4" />
                            快充 ({getChargingPower('fast')}kW)
                          </div>
                        </SelectItem>
                        <SelectItem value="slow">
                          <div className="flex items-center">
                            <Battery className="mr-2 h-4 w-4" />
                            慢充 ({getChargingPower('slow')}kW)
                          </div>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="requested_amount">充电量 (kWh)</Label>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600 dark:text-gray-400">当前选择：</span>
                        <span className="font-semibold text-lg">{parseFloat(watchedValues.requested_amount) || 1} kWh</span>
                      </div>
                      <div className="px-2">
                        <Slider
                          value={[parseFloat(watchedValues.requested_amount) || 1]}
                          onValueChange={([value]) => form.setValue('requested_amount', parseFloat(value) || 1)}
                          max={selectedVehicle.battery_capacity}
                          min={1}
                          step={.1}
                          className="w-full"
                        />
                        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-2">
                          <span>1 kWh</span>
                          <span>{selectedVehicle.battery_capacity} kWh</span>
                        </div>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500">
                      建议充电量：{Math.round(selectedVehicle.battery_capacity * 0.8)}kWh (80%)
                    </p>
                  </div>
                </div>

                {/* 预计信息 */}
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm flex items-center">
                      <Clock className="mr-2 h-4 w-4" />
                      精确估算
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {estimation && !estimation.error ? (
                      <>
                        {/* 基础信息 */}
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div className="flex justify-between">
                            <span className="text-gray-600 dark:text-gray-400">预计费用：</span>
                            <span className="font-semibold text-green-600">
                              {formatCurrency(estimation.summary.total_cost)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-600 dark:text-gray-400">总用时：</span>
                            <span className="font-semibold">
                              {estimation.summary.total_time_display}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-600 dark:text-gray-400">等待时间：</span>
                            <span className="font-semibold text-amber-600">
                              {estimation.summary.wait_time_display}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-600 dark:text-gray-400">充电时间：</span>
                            <span className="font-semibold text-blue-600">
                              {estimation.summary.charging_time_display}
                            </span>
                          </div>
                        </div>

                        {/* 队列详情 */}
                        {estimation.wait_time && (
                          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
                            <div className="text-sm space-y-1">
                              <div className="flex justify-between">
                                <span className="text-blue-700 dark:text-blue-300">排队位置：</span>
                                <span className="font-medium">第 {estimation.wait_time.queue_position} 位</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-blue-700 dark:text-blue-300">前方等待：</span>
                                <span className="font-medium">{estimation.wait_time.ahead_count} 人</span>
                              </div>
                              {estimation.wait_time.best_pile && (
                                <div className="flex justify-between">
                                  <span className="text-blue-700 dark:text-blue-300">推荐桩：</span>
                                  <span className="font-medium">{estimation.wait_time.best_pile.pile_id}</span>
                                </div>
                              )}
                              <div className="text-xs text-blue-600 dark:text-blue-400 mt-2 border-t pt-2">
                                <div className="font-medium mb-1">等待时间详情：</div>
                                <div>{estimation.wait_time.pile_details}</div>
                                {estimation.wait_time.additional_queue_wait > 0 && (
                                  <div>外部等候区: +{estimation.wait_time.additional_queue_wait}分钟</div>
                                )}
                              </div>
                            </div>
                          </div>
                        )}

                        {/* 费用明细 */}
                        {estimation.cost_breakdown && (
                          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
                            <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                              费用明细 (基于预计充电时间段)
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              {estimation.cost_breakdown.peak_cost > 0 && (
                                <div className="flex justify-between">
                                  <span className="text-red-600">峰时：</span>
                                  <span>{formatCurrency(estimation.cost_breakdown.peak_cost)}</span>
                                </div>
                              )}
                              {estimation.cost_breakdown.normal_cost > 0 && (
                                <div className="flex justify-between">
                                  <span className="text-yellow-600">平时：</span>
                                  <span>{formatCurrency(estimation.cost_breakdown.normal_cost)}</span>
                                </div>
                              )}
                              {estimation.cost_breakdown.valley_cost > 0 && (
                                <div className="flex justify-between">
                                  <span className="text-green-600">谷时：</span>
                                  <span>{formatCurrency(estimation.cost_breakdown.valley_cost)}</span>
                                </div>
                              )}
                              <div className="flex justify-between">
                                <span className="text-blue-600">服务费：</span>
                                <span>{formatCurrency(estimation.cost_breakdown.service_cost)}</span>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* 时间建议 */}
                        {timeSuggestions && timeSuggestions.length > 0 && (
                          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
                            <div className="text-xs font-medium text-green-700 dark:text-green-300 mb-2">
                              💡 省钱提示
                            </div>
                            {timeSuggestions.map((suggestion, index) => (
                              <div key={index} className="text-xs text-green-600 dark:text-green-400">
                                {suggestion.description} ({suggestion.time_range})
                                {suggestion.savings && (
                                  <span className="ml-1">可节省 {suggestion.savings}%</span>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                        {estimation?.error || '正在计算估算信息...'}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* 提交按钮 */}
                <div className="flex justify-end space-x-3 pt-4">
                  <Button 
                    type="button" 
                    variant="outline" 
                    onClick={() => setDialogOpen(false)}
                  >
                    取消
                  </Button>
                  <Button 
                    type="submit" 
                    disabled={!watchedValues.vehicle_id || submitting}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    {submitting ? '提交中...' : '提交请求'}
                  </Button>
                </div>
              </>
            )}
          </form>
        </DialogContent>
      </Dialog>

      {/* 确认对话框 */}
      <AlertDialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认提交充电请求</AlertDialogTitle>
            <AlertDialogDescription>
              请确认您的充电请求信息无误后提交
            </AlertDialogDescription>
          </AlertDialogHeader>
          
          {requestData && (
            <div className="space-y-4">
              <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg space-y-2">
                <div className="flex justify-between">
                  <span>车辆：</span>
                  <span className="font-semibold">
                    {vehicles.find(v => v.id.toString() === requestData.vehicle_id)?.license_plate}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>充电模式：</span>
                  <Badge variant={requestData.charging_mode === 'fast' ? 'default' : 'secondary'}>
                    {requestData.charging_mode === 'fast' ? '快充' : '慢充'}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>充电量：</span>
                  <span className="font-semibold">{requestData.requested_amount} kWh</span>
                </div>
              </div>

              {/* 使用estimation数据显示精确信息 */}
              {estimation && !estimation.error && (
                <div className="space-y-3">
                  <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
                    <div className="text-sm font-medium text-blue-700 dark:text-blue-300 mb-2">
                      ⏰ 时间估算
                    </div>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span>等待时间：</span>
                        <span className="font-semibold text-amber-600">
                          {estimation.summary.wait_time_display}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>充电时间：</span>
                        <span className="font-semibold text-blue-600">
                          {estimation.summary.charging_time_display}
                        </span>
                      </div>
                      <div className="flex justify-between border-t pt-1">
                        <span className="font-medium">总用时：</span>
                        <span className="font-bold">{estimation.summary.total_time_display}</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-green-50 dark:bg-green-900/20 p-3 rounded-lg">
                    <div className="text-sm font-medium text-green-700 dark:text-green-300 mb-2">
                      💰 费用估算
                    </div>
                    <div className="space-y-1 text-sm">
                      {estimation.cost_breakdown && (
                        <>
                          {estimation.cost_breakdown.peak_cost > 0 && (
                            <div className="flex justify-between">
                              <span className="text-red-600">峰时：</span>
                              <span>{formatCurrency(estimation.cost_breakdown.peak_cost)}</span>
                            </div>
                          )}
                          {estimation.cost_breakdown.normal_cost > 0 && (
                            <div className="flex justify-between">
                              <span className="text-yellow-600">平时：</span>
                              <span>{formatCurrency(estimation.cost_breakdown.normal_cost)}</span>
                            </div>
                          )}
                          {estimation.cost_breakdown.valley_cost > 0 && (
                            <div className="flex justify-between">
                              <span className="text-green-600">谷时：</span>
                              <span>{formatCurrency(estimation.cost_breakdown.valley_cost)}</span>
                            </div>
                          )}
                          <div className="flex justify-between">
                            <span className="text-blue-600">服务费：</span>
                            <span>{formatCurrency(estimation.cost_breakdown.service_cost)}</span>
                          </div>
                        </>
                      )}
                      <div className="flex justify-between border-t pt-1">
                        <span className="font-medium">总费用：</span>
                        <span className="font-bold text-green-600 text-lg">
                          {formatCurrency(estimation.summary.total_cost)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              <p className="text-sm text-gray-600 dark:text-gray-400">
                提交后系统将为您智能分配充电桩，请保持车辆准备状态。
              </p>
            </div>
          )}

          <AlertDialogFooter>
            <AlertDialogCancel disabled={submitting}>取消</AlertDialogCancel>
            <AlertDialogAction 
              onClick={confirmSubmitRequest} 
              disabled={submitting}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {submitting ? '提交中...' : '确认提交'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
} 