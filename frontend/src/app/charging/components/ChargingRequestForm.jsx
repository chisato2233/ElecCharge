'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Slider } from '@/components/ui/slider';
import { Car, Zap, Battery, Calculator } from 'lucide-react';

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

export default function ChargingRequestForm({
  form,
  vehicles,
  systemParams,
  queueStatus,
  submitting,
  onSubmit,
  onVehicleChange,
  activeRequests = []  // 添加activeRequests参数
}) {
  const watchedValues = form.watch();

  // 获取车辆状态的函数
  const getVehicleStatus = (vehicle) => {
    const activeRequest = activeRequests.find(req => 
      req.vehicle_info && req.vehicle_info.license_plate === vehicle.license_plate
    );
    
    if (!activeRequest) {
      return { status: 'available', text: '可用', color: 'text-green-600 dark:text-green-400' };
    }
    
    switch (activeRequest.current_status) {
      case 'waiting':
        return { 
          status: 'waiting', 
          text: `排队中 (第${activeRequest.queue_position}位)`, 
          color: 'text-yellow-600 dark:text-yellow-400' 
        };
      case 'charging':
        const progress = activeRequest.current_amount && activeRequest.requested_amount 
          ? Math.round((activeRequest.current_amount / activeRequest.requested_amount) * 100)
          : 0;
        return { 
          status: 'charging', 
          text: `充电中 (${progress}%)`, 
          color: 'text-blue-600 dark:text-blue-400' 
        };
      default:
        return { status: 'available', text: '可用', color: 'text-green-600 dark:text-green-400' };
    }
  };

  // 车辆是否可选择
  const isVehicleAvailable = (vehicle) => {
    const vehicleStatus = getVehicleStatus(vehicle);
    return vehicleStatus.status === 'available';
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

  const calculateEstimatedTime = () => {
    const amount = watchedValues.requested_amount;
    const mode = watchedValues.charging_mode;
    
    // 快充功率约120kW，慢充约7kW
    const power = mode === 'fast' ? 120 : 7;
    return Math.ceil(amount / power * 60); // 分钟
  };

  const getQueueWaitTime = () => {
    if (!queueStatus) return 0;
    
    const mode = watchedValues.charging_mode;
    const modeData = mode === 'fast' ? queueStatus.fast_charging : queueStatus.slow_charging;
    
    return modeData.waiting_count * 30; // 假设每个请求平均30分钟
  };

  // 获取状态图标
  const getStatusIcon = (status) => {
    switch (status) {
      case 'available':
        return <span className="inline-block w-2 h-2 bg-green-500 rounded-full mr-2"></span>;
      case 'waiting':
        return <span className="inline-block w-2 h-2 bg-yellow-500 rounded-full mr-2"></span>;
      case 'charging':
        return <span className="inline-block w-2 h-2 bg-blue-500 rounded-full mr-2 animate-pulse"></span>;
      default:
        return <span className="inline-block w-2 h-2 bg-gray-500 rounded-full mr-2"></span>;
    }
  };

  // 统计车辆状态
  const vehicleStats = vehicles.reduce((stats, vehicle) => {
    const status = getVehicleStatus(vehicle).status;
    stats[status] = (stats[status] || 0) + 1;
    return stats;
  }, {});

  return (
    <Card>
      <CardHeader>
        <CardTitle>充电请求</CardTitle>
        <CardDescription>
          请选择车辆和充电参数
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* 车辆状态概览 */}
            {vehicles.length > 0 && (
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 mb-4">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  车辆状态概览
                </h4>
                <div className="flex flex-wrap gap-4 text-xs">
                  <div className="flex items-center">
                    <span className="inline-block w-2 h-2 bg-green-500 rounded-full mr-1"></span>
                    <span className="text-gray-600 dark:text-gray-400">
                      可用 ({vehicleStats.available || 0}辆)
                    </span>
                  </div>
                  <div className="flex items-center">
                    <span className="inline-block w-2 h-2 bg-yellow-500 rounded-full mr-1"></span>
                    <span className="text-gray-600 dark:text-gray-400">
                      排队中 ({vehicleStats.waiting || 0}辆)
                    </span>
                  </div>
                  <div className="flex items-center">
                    <span className="inline-block w-2 h-2 bg-blue-500 rounded-full mr-1 animate-pulse"></span>
                    <span className="text-gray-600 dark:text-gray-400">
                      充电中 ({vehicleStats.charging || 0}辆)
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* 车辆选择 */}
            <FormField
              control={form.control}
              name="vehicle_id"
              rules={{ required: '请选择车辆' }}
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center">
                    <Car className="mr-2 h-4 w-4" />
                    选择车辆
                  </FormLabel>
                  <Select onValueChange={(value) => {
                    field.onChange(value);
                    onVehicleChange(value);
                  }} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="请选择要充电的车辆" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {vehicles.map((vehicle) => {
                        const vehicleStatus = getVehicleStatus(vehicle);
                        const isAvailable = isVehicleAvailable(vehicle);
                        
                        return (
                          <SelectItem 
                            key={vehicle.id} 
                            value={vehicle.id.toString()}
                            disabled={!isAvailable}
                            className={!isAvailable ? 'opacity-60' : ''}
                          >
                            <div className="flex items-center justify-between w-full">
                              <div className="flex items-center">
                                {getStatusIcon(vehicleStatus.status)}
                                <span className={`font-medium ${!isAvailable ? 'text-gray-400' : ''}`}>
                                  {vehicle.license_plate}
                                </span>
                              </div>
                              <div className="flex items-center space-x-3 text-sm">
                                <span className={vehicleStatus.color}>
                                  {vehicleStatus.text}
                                </span>
                                <span className="text-gray-500 dark:text-gray-400">
                                  {vehicle.battery_capacity}kWh
                                </span>
                                {vehicle.is_default && <Badge variant="outline" className="text-xs">默认</Badge>}
                              </div>
                            </div>
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                  
                  {/* 车辆状态提示 */}
                  {field.value && (
                    <div className="mt-2">
                      {(() => {
                        const selectedVehicle = vehicles.find(v => v.id.toString() === field.value);
                        if (!selectedVehicle) return null;
                        
                        const status = getVehicleStatus(selectedVehicle);
                        if (status.status !== 'available') {
                          return (
                            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                              <div className="flex items-center">
                                {getStatusIcon(status.status)}
                                <span className="text-sm text-amber-800 dark:text-amber-200">
                                  该车辆当前{status.text}，无法提交新的充电请求
                                </span>
                              </div>
                            </div>
                          );
                        }
                        return (
                          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
                            <div className="flex items-center">
                              {getStatusIcon(status.status)}
                              <span className="text-sm text-green-800 dark:text-green-200">
                                车辆可用，可以提交充电请求
                              </span>
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  )}
                </FormItem>
              )}
            />

            {/* 充电模式 */}
            <FormField
              control={form.control}
              name="charging_mode"
              render={({ field }) => (
                <FormItem className="space-y-3">
                  <FormLabel className="flex items-center">
                    <Zap className="mr-2 h-4 w-4" />
                    充电模式
                  </FormLabel>
                  <FormControl>
                    <RadioGroup
                      onValueChange={field.onChange}
                      value={field.value}
                      className="flex space-x-6"
                    >
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="fast" id="fast" />
                        <label htmlFor="fast" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                          快充模式
                        </label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="slow" id="slow" />
                        <label htmlFor="slow" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                          慢充模式
                        </label>
                      </div>
                    </RadioGroup>
                  </FormControl>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    {watchedValues.charging_mode === 'fast' ? 
                      '快充模式：约120kW功率，适合紧急补电' : 
                      '慢充模式：约7kW功率，适合长时间停车'}
                  </div>
                </FormItem>
              )}
            />

            {/* 充电量选择 */}
            <FormField
              control={form.control}
              name="requested_amount"
              rules={{ 
                required: '请设置充电量',
                min: { value: 5, message: '充电量不能小于5kWh' },
                max: { value: watchedValues.battery_capacity, message: '充电量不能超过电池容量' }
              }}
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center justify-between">
                    <span className="flex items-center">
                      <Battery className="mr-2 h-4 w-4" />
                      充电量 (kWh)
                    </span>
                    <span className="text-sm font-normal text-gray-600 dark:text-gray-400">
                      电池容量: {watchedValues.battery_capacity} kWh
                    </span>
                  </FormLabel>
                  <FormControl>
                    <div className="space-y-4">
                      <Slider
                        value={[field.value]}
                        onValueChange={([value]) => field.onChange(Math.round(value * 10) / 10)}
                        max={watchedValues.battery_capacity}
                        min={5}
                        step={0.1}
                        className="w-full"
                      />
                      <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
                        <span>5 kWh</span>
                        <span className="font-semibold text-lg text-gray-900 dark:text-white">
                          {field.value.toFixed(1)} kWh
                        </span>
                        <span>{watchedValues.battery_capacity} kWh</span>
                      </div>
                      <Input
                        type="number"
                        value={field.value}
                        onChange={(e) => field.onChange(Number(e.target.value))}
                        min={5}
                        max={watchedValues.battery_capacity}
                        step={0.1}
                        className="mt-2"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 费用和时间估算 */}
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-3">
              <h3 className="font-medium flex items-center text-gray-900 dark:text-white">
                <Calculator className="mr-2 h-4 w-4" />
                费用与时间估算
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">预计费用：</span>
                  <span className="font-semibold text-gray-900 dark:text-white">
                    ¥{calculateEstimatedCost().toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">充电时间：</span>
                  <span className="font-semibold text-gray-900 dark:text-white">
                    {formatTimeEstimate(calculateEstimatedTime())}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">等待时间：</span>
                  <span className="font-semibold text-gray-900 dark:text-white">
                    {formatTimeEstimate(getQueueWaitTime())}
                  </span>
                </div>
              </div>
              
              {systemParams?.pricing && (
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                  <div className="grid grid-cols-2 gap-2">
                    <div>峰时电价: ¥{systemParams.pricing.peak_rate}/kWh</div>
                    <div>平时电价: ¥{systemParams.pricing.normal_rate}/kWh</div>
                    <div>谷时电价: ¥{systemParams.pricing.valley_rate}/kWh</div>
                    <div>服务费: ¥{systemParams.pricing.service_rate}/kWh</div>
                  </div>
                </div>
              )}
            </div>

            {/* 提交按钮 */}
            <div className="flex justify-end">
              <Button 
                type="submit" 
                disabled={submitting || (watchedValues.vehicle_id && !isVehicleAvailable(vehicles.find(v => v.id.toString() === watchedValues.vehicle_id)))} 
                className="bg-blue-600 hover:bg-blue-700"
              >
                {submitting ? '提交中...' : '提交充电请求'}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
} 