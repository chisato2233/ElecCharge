'use client';

import { useState } from 'react';
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

  const form = useForm({
    defaultValues: {
      vehicle_id: '',
      charging_mode: 'fast',
      requested_amount: 50,
      battery_capacity: 75
    }
  });

  const watchedValues = form.watch();

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
    const modeData = mode === 'fast' ? queueStatus.fast_charging : queueStatus.slow_charging;
    
    return modeData ? modeData.waiting_count * 30 : 0; // 假设每个请求平均30分钟
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
                            快充 (120kW)
                          </div>
                        </SelectItem>
                        <SelectItem value="slow">
                          <div className="flex items-center">
                            <Battery className="mr-2 h-4 w-4" />
                            慢充 (7kW)
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
                      预计信息
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">预计费用：</span>
                      <span className="font-semibold">¥{estimatedCost.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">预计等待：</span>
                      <span className="font-semibold">{formatTimeEstimate(waitTime)}</span>
                    </div>
                    {queueStatus && (
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">当前排队：</span>
                        <span className="font-semibold">
                          {watchedValues.charging_mode === 'fast' 
                            ? queueStatus.fast_charging?.waiting_count || 0
                            : queueStatus.slow_charging?.waiting_count || 0
                          } 人
                        </span>
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
                <div className="flex justify-between">
                  <span>预计费用：</span>
                  <span className="font-semibold text-green-600">¥{estimatedCost.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span>预计等待：</span>
                  <span className="font-semibold text-blue-600">{formatTimeEstimate(waitTime)}</span>
                </div>
              </div>
              
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