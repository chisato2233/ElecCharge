'use client';

import { useState, useEffect } from 'react';
import Layout from '@/components/layout/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Slider } from '@/components/ui/slider';
import { Progress } from '@/components/ui/progress';
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
import { 
  Car, 
  Zap, 
  Clock, 
  Battery, 
  Calculator,
  Users,
  MapPin,
  AlertCircle,
  CheckCircle,
  Info
} from 'lucide-react';
import { vehicleAPI } from '@/lib/vehicles';
import { chargingAPI } from '@/lib/charging';
import { toast } from 'sonner';
import { useForm } from 'react-hook-form';

export default function ChargingPage() {
  const [vehicles, setVehicles] = useState([]);
  const [queueStatus, setQueueStatus] = useState(null);
  const [pilesStatus, setPilesStatus] = useState(null);
  const [systemParams, setSystemParams] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [currentRequest, setCurrentRequest] = useState(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
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

  useEffect(() => {
    fetchInitialData();
    // 每30秒更新系统状态（不包含用户请求）
    const interval = setInterval(fetchStatusData, 30000);
    return () => clearInterval(interval);
  }, []);

  // 监听当前请求状态变化，启动或停止用户状态轮询
  useEffect(() => {
    let userStatusInterval;
    
    if (currentRequest && ['waiting', 'charging'].includes(currentRequest.current_status)) {
      // 启动用户状态轮询
      userStatusInterval = setInterval(async () => {
        try {
          const response = await chargingAPI.getRequestStatus();
          const request = response.data;
          setCurrentRequest(request);
          
          // 如果请求已完成或取消，停止轮询
          if (!request || !['waiting', 'charging'].includes(request.current_status)) {
            setCurrentRequest(null);
          }
        } catch (error) {
          // 请求不存在，清除当前请求
          setCurrentRequest(null);
        }
      }, 10000); // 10秒间隔
    }
    
    return () => {
      if (userStatusInterval) {
        clearInterval(userStatusInterval);
      }
    };
  }, [currentRequest?.current_status]);

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      await Promise.all([
        fetchVehicles(),
        fetchStatusData(),
        fetchSystemParams(),
        checkCurrentRequest()
      ]);
    } catch (error) {
      console.error('获取初始数据失败:', error);
      toast.error('获取数据失败，请刷新页面重试');
    } finally {
      setLoading(false);
    }
  };

  const fetchVehicles = async () => {
    try {
      const response = await vehicleAPI.getVehicles();
      if (response.success) {
        setVehicles(response.data);
        
        // 自动选择默认车辆
        const defaultVehicle = response.data.find(v => v.is_default);
        if (defaultVehicle) {
          form.setValue('vehicle_id', defaultVehicle.id.toString());
          form.setValue('battery_capacity', defaultVehicle.battery_capacity);
        }
      }
    } catch (error) {
      console.error('获取车辆列表失败:', error);
    }
  };

  const fetchStatusData = async () => {
    try {
      const [queueRes, pilesRes] = await Promise.all([
        chargingAPI.getQueueStatus(),
        chargingAPI.getPilesStatus()
      ]);
      
      if (queueRes.success) setQueueStatus(queueRes.data);
      if (pilesRes.success) setPilesStatus(pilesRes.data);
    } catch (error) {
      console.error('获取状态数据失败:', error);
    }
  };

  const fetchSystemParams = async () => {
    try {
      const response = await chargingAPI.getSystemParameters();
      if (response.success) {
        setSystemParams(response.data);
      }
    } catch (error) {
      console.error('获取系统参数失败:', error);
    }
  };

  const checkCurrentRequest = async () => {
    try {
      const response = await chargingAPI.getRequestStatus();
      if (response.success) {
        setCurrentRequest(response.data);
      }
    } catch (error) {
      // 没有当前请求是正常的，不再输出错误日志
      setCurrentRequest(null);
    }
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

  const handleSubmit = (data) => {
    setRequestData(data);
    setShowConfirmDialog(true);
  };

  const confirmSubmitRequest = async () => {
    try {
      setSubmitting(true);
      
      const vehicle = vehicles.find(v => v.id.toString() === requestData.vehicle_id);
      const submitData = {
        charging_mode: requestData.charging_mode,
        requested_amount: requestData.requested_amount,
        battery_capacity: vehicle.battery_capacity
      };
      
      const response = await chargingAPI.submitRequest(submitData);
      
      if (response.success) {
        toast.success('充电请求提交成功！');
        setCurrentRequest(response.data);
        setShowConfirmDialog(false);
        form.reset();
      }
    } catch (error) {
      console.error('提交充电请求失败:', error);
      const errorMessage = error.response?.data?.error?.message || '提交失败';
      toast.error(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelRequest = async () => {
    if (!currentRequest) return;
    
    try {
      const response = await chargingAPI.cancelRequest(currentRequest.id);
      if (response.success) {
        toast.success('充电请求已取消');
        setCurrentRequest(null);
      }
    } catch (error) {
      console.error('取消请求失败:', error);
      toast.error('取消请求失败');
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-300">加载中...</p>
          </div>
        </div>
      </Layout>
    );
  }

  // 如果有当前请求，显示状态页面
  if (currentRequest) {
    return (
      <Layout>
        <div className="px-4 py-6 sm:px-0">
          <div className="max-w-4xl mx-auto">
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">充电状态</h1>
              <p className="mt-2 text-gray-600 dark:text-gray-300">您的充电请求状态</p>
            </div>

            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Zap className="mr-2 h-5 w-5" />
                  当前充电请求
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">队列号：</span>
                      <span className="font-semibold text-gray-900 dark:text-white">{currentRequest.queue_number}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">充电模式：</span>
                      <Badge variant={currentRequest.charging_mode === 'fast' ? 'default' : 'secondary'}>
                        {currentRequest.charging_mode === 'fast' ? '快充' : '慢充'}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">请求电量：</span>
                      <span className="font-semibold text-gray-900 dark:text-white">{currentRequest.requested_amount} kWh</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">当前状态：</span>
                      <Badge variant={
                        currentRequest.current_status === 'charging' ? 'default' :
                        currentRequest.current_status === 'waiting' ? 'secondary' : 'outline'
                      }>
                        {currentRequest.current_status === 'charging' ? '充电中' :
                         currentRequest.current_status === 'waiting' ? '等待中' : '已完成'}
                      </Badge>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    {currentRequest.current_status === 'waiting' && (
                      <>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">排队位置：</span>
                          <span className="font-semibold text-gray-900 dark:text-white">第 {currentRequest.queue_position} 位</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">前方等待：</span>
                          <span className="font-semibold text-gray-900 dark:text-white">{currentRequest.ahead_count} 人</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">预计等待：</span>
                          <span className="font-semibold text-gray-900 dark:text-white">{Math.round(currentRequest.estimated_wait_time / 60)} 小时</span>
                        </div>
                      </>
                    )}
                    
                    {currentRequest.current_status === 'charging' && (
                      <>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">充电桩：</span>
                          <span className="font-semibold text-gray-900 dark:text-white">{currentRequest.charging_pile_id}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">已充电量：</span>
                          <span className="font-semibold text-gray-900 dark:text-white">{currentRequest.current_amount} kWh</span>
                        </div>
                        <div className="w-full">
                          <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
                            <span>充电进度</span>
                            <span>{Math.round((currentRequest.current_amount / currentRequest.requested_amount) * 100)}%</span>
                          </div>
                          <Progress 
                            value={(currentRequest.current_amount / currentRequest.requested_amount) * 100} 
                            className="w-full"
                          />
                        </div>
                      </>
                    )}
                  </div>
                </div>
                
                <div className="mt-6 flex justify-end space-x-3">
                  {currentRequest.current_status === 'waiting' && (
                    <Button
                      onClick={handleCancelRequest}
                      variant="outline"
                      className="text-red-600 border-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                    >
                      取消请求
                    </Button>
                  )}
                  
                  {currentRequest.current_status === 'charging' && (
                    <Button
                      onClick={async () => {
                        try {
                          const response = await chargingAPI.completeCharging();
                          if (response.success) {
                            toast.success('充电已结束');
                            setCurrentRequest(null);
                          }
                        } catch (error) {
                          toast.error('结束充电失败');
                        }
                      }}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      结束充电
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="px-4 py-6 sm:px-0">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">发起充电请求</h1>
            <p className="mt-2 text-gray-600 dark:text-gray-300">选择车辆和充电参数，提交充电请求</p>
          </div>

          {/* 充电站状态概览 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">快充桩状态</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {pilesStatus?.fast_piles?.filter(p => p.status === 'normal' && !p.is_working).length || 0}
                  /
                  {pilesStatus?.fast_piles?.length || 0}
                </div>
                <p className="text-xs text-muted-foreground">可用/总数</p>
                <div className="mt-2">
                  <Badge variant="secondary" className="text-xs">
                    等待: {queueStatus?.fast_charging?.waiting_count || 0}人
                  </Badge>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">慢充桩状态</CardTitle>
                <Battery className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {pilesStatus?.slow_piles?.filter(p => p.status === 'normal' && !p.is_working).length || 0}
                  /
                  {pilesStatus?.slow_piles?.length || 0}
                </div>
                <p className="text-xs text-muted-foreground">可用/总数</p>
                <div className="mt-2">
                  <Badge variant="secondary" className="text-xs">
                    等待: {queueStatus?.slow_charging?.waiting_count || 0}人
                  </Badge>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">等候区</CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {queueStatus?.waiting_area_capacity?.current || 0}
                  /
                  {queueStatus?.waiting_area_capacity?.max || 0}
                </div>
                <p className="text-xs text-muted-foreground">当前/容量</p>
                <div className="mt-2">
                  <Progress 
                    value={queueStatus?.waiting_area_capacity ? 
                      (queueStatus.waiting_area_capacity.current / queueStatus.waiting_area_capacity.max) * 100 : 0
                    } 
                    className="h-2"
                  />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 充电请求表单 */}
          <Card>
            <CardHeader>
              <CardTitle>充电请求</CardTitle>
              <CardDescription>
                请选择车辆和充电参数
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
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
                          handleVehicleChange(value);
                        }} value={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="请选择要充电的车辆" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {vehicles.map((vehicle) => (
                              <SelectItem key={vehicle.id} value={vehicle.id.toString()}>
                                <div className="flex items-center justify-between w-full">
                                  <span className="font-medium">{vehicle.license_plate}</span>
                                  <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
                                    <span>{vehicle.battery_capacity}kWh</span>
                                    {vehicle.is_default && <Badge variant="outline" className="text-xs">默认</Badge>}
                                  </div>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
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
                              onValueChange={([value]) => field.onChange(value)}
                              max={watchedValues.battery_capacity}
                              min={5}
                              step={5}
                              className="w-full"
                            />
                            <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
                              <span>5 kWh</span>
                              <span className="font-semibold text-lg text-gray-900 dark:text-white">
                                {field.value} kWh
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
                          约 {Math.ceil(calculateEstimatedTime() / 60)} 小时
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">等待时间：</span>
                        <span className="font-semibold text-gray-900 dark:text-white">
                          约 {Math.ceil(getQueueWaitTime() / 60)} 小时
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
                  <div className="flex justify-end space-x-3 pt-6">
                    <Button type="button" variant="outline" onClick={() => form.reset()}>
                      重置
                    </Button>
                    <Button type="submit" disabled={submitting || vehicles.length === 0}>
                      {submitting ? '提交中...' : '提交充电请求'}
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>

          {/* 确认对话框 */}
          <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
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
                            约 {Math.ceil(getQueueWaitTime() / 60)} 小时
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
                  onClick={confirmSubmitRequest}
                  disabled={submitting}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {submitting ? '提交中...' : '确认提交'}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
    </Layout>
  );
} 