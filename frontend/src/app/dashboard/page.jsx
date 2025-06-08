'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Zap, 
  Clock, 
  Users, 
  Battery, 
  TrendingUp,
  AlertCircle 
} from 'lucide-react';
import { chargingAPI } from '@/lib/charging';
import { vehicleAPI } from '@/lib/vehicles';
import { BgAnimateButton } from '@/components/ui/bg-animate-button';
import { AnimatedNumber } from '@/components/ui/AnimatedNumber';
import PageTransition, { cardVariants, containerVariants, itemVariants } from '@/components/layout/PageTransition';
import { toast } from 'sonner';
import ChargingRequestDialog from '../charging/components/ChargingRequestDialog';

export default function DashboardPage() {
  const [queueStatus, setQueueStatus] = useState(null);
  const [pilesStatus, setPilesStatus] = useState(null);
  const [userRequest, setUserRequest] = useState(null);
  const [hasCheckedUserRequest, setHasCheckedUserRequest] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // 添加ChargingRequestDialog所需的状态
  const [vehicles, setVehicles] = useState([]);
  const [systemParams, setSystemParams] = useState(null);
  const [activeRequests, setActiveRequests] = useState([]);

  useEffect(() => {
    fetchData();
    // 每15秒刷新系统状态数据
    const interval = setInterval(fetchSystemStatus, 200);
    return () => clearInterval(interval);
  }, []);

  // 系统状态轮询（不包含用户请求）
  const fetchSystemStatus = async () => {
    try {
      const [queueData, pilesData] = await Promise.all([
        chargingAPI.getEnhancedQueueStatus(), // 使用增强的队列状态API
        chargingAPI.getPilesStatus()
      ]);

      setQueueStatus(queueData.data);
      setPilesStatus(pilesData.data);
    } catch (error) {
      console.error('获取系统状态失败:', error);
    }
  };

  // 完整数据获取（首次加载时使用）
  const fetchData = async () => {
    try {
      // 先获取系统状态
      await fetchSystemStatus();
      
      // 检查用户当前请求状态
      await checkUserRequest();
      
      // 获取充电对话框所需的数据
      await Promise.all([
        fetchVehicles(),
        fetchSystemParams(),
        fetchActiveRequests()
      ]);
    } catch (error) {
      console.error('获取数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 检查用户请求状态
  const checkUserRequest = async () => {
    try {
      const requestData = await chargingAPI.getRequestStatus();
      setUserRequest(requestData.data);
      setHasCheckedUserRequest(true);
      
      // 如果有活跃请求，启动用户状态轮询
      if (requestData.data && ['waiting', 'charging'].includes(requestData.data.current_status)) {
        startUserStatusPolling();
      }
    } catch (error) {
      // 用户没有活跃请求是正常的
      setUserRequest(null);
      setHasCheckedUserRequest(true);
    }
  };

  // 用户状态轮询（仅在有活跃请求时）
  const startUserStatusPolling = () => {
    const userInterval = setInterval(async () => {
      try {
        const requestData = await chargingAPI.getRequestStatus();
        const request = requestData.data;
        setUserRequest(request);
        
        // 如果请求已完成或取消，停止轮询
        if (!request || !['waiting', 'charging'].includes(request.current_status)) {
          clearInterval(userInterval);
          setUserRequest(null);
        }
      } catch (error) {
        // 请求不存在，停止轮询
        clearInterval(userInterval);
        setUserRequest(null);
      }
    }, 10000); // 用户状态轮询间隔更短（10秒）

    // 组件卸载时清理
    return () => clearInterval(userInterval);
  };

  // 获取车辆列表
  const fetchVehicles = async () => {
    try {
      const response = await vehicleAPI.getVehicles();
      if (response.success) {
        setVehicles(response.data);
      }
    } catch (error) {
      console.error('获取车辆列表失败:', error);
    }
  };

  // 获取系统参数
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

  // 获取活跃请求
  const fetchActiveRequests = async () => {
    try {
      const response = await chargingAPI.getAllActiveRequests();
      if (response.success) {
        setActiveRequests(response.data || []);
      }
    } catch (error) {
      // 没有活跃请求是正常的
      setActiveRequests([]);
    }
  };

  // 处理请求更新
  const handleRequestUpdate = async () => {
    // 当请求状态更新时，重新获取用户请求和活跃请求列表
    await Promise.all([
      checkUserRequest(),
      fetchActiveRequests()
    ]);
  };

  if (loading) {
    return (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-300">加载中...</p>
          </div>
        </div>
    );
  }

  return (
    <PageTransition>
      <div className="px-4 py-6 sm:px-0 bg-white dark:bg-black min-h-screen">
        <motion.div 
          className="mb-8"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <motion.h1 
            className="text-3xl font-bold text-gray-900 dark:text-white"
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            充电站仪表板
          </motion.h1>
          <motion.p 
            className="mt-2 text-gray-600 dark:text-gray-300"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            实时监控充电站状态和您的充电请求
          </motion.p>
        </motion.div>

        {/* 用户当前请求状态 */}
        {userRequest && (
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <Card className="mb-6 border-blue-200 dark:border-blue-800 shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center">
                <Zap className="mr-2 h-5 w-5 text-blue-600 dark:text-blue-400" />
                您的充电状态
              </CardTitle>
            </CardHeader>
            <CardContent>
                              <motion.div 
                className="grid grid-cols-1 md:grid-cols-4 gap-4"
                variants={containerVariants}
                initial="hidden"
                animate="visible"
              >
                <motion.div variants={itemVariants}>
                <p className="text-sm text-gray-600 dark:text-gray-400">队列号</p>
                  <p className="text-lg font-semibold text-gray-900 dark:text-white">
                    {userRequest.queue_number || '未分配'}
                  </p>
                </motion.div>
                <motion.div variants={itemVariants}>
                <p className="text-sm text-gray-600 dark:text-gray-400">当前状态</p>
                <Badge variant={userRequest.current_status === 'charging' ? 'default' : 'secondary'}>
                  {userRequest.current_status === 'waiting' ? '等待中' : 
                   userRequest.current_status === 'charging' ? '充电中' : '已完成'}
                </Badge>
                </motion.div>
                <motion.div variants={itemVariants}>
                <p className="text-sm text-gray-600 dark:text-gray-400">队列位置</p>
                  <div className="flex flex-col">
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      {userRequest.queue_level === 'external_waiting' ? '🚪 外部等候区' : 
                       userRequest.queue_level === 'pile_queue' ? '🔌 桩队列' : 
                       userRequest.queue_level === 'charging' ? '⚡ 充电中' : '待分配'}
                    </p>
                    {(userRequest.external_queue_position || userRequest.pile_queue_position) && (
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        第 {userRequest.external_queue_position || userRequest.pile_queue_position} 位
                        {userRequest.charging_pile && ` (${userRequest.charging_pile})`}
                      </p>
                    )}
                    {userRequest.queue_info && (
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {userRequest.queue_info.description}
                      </p>
                    )}
                  </div>
                </motion.div>
                <motion.div variants={itemVariants}>
                <p className="text-sm text-gray-600 dark:text-gray-400">预计等待时间</p>
                  <p className="text-lg font-semibold text-gray-900 dark:text-white">
                    <AnimatedNumber value={userRequest.estimated_wait_time} /> 分钟
                  </p>
                </motion.div>
              </motion.div>
              
              {userRequest.current_status === 'charging' && (
                  <motion.div 
                    className="mt-4"
                    initial={{ opacity: 0, scaleX: 0 }}
                    animate={{ opacity: 1, scaleX: 1 }}
                    transition={{ duration: 0.8, delay: 0.5 }}
                  >
                  <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
                    <span>充电进度</span>
                      <span>
                        <AnimatedNumber 
                          value={userRequest.current_amount} 
                          precision={1}
                        /> / 
                        <AnimatedNumber 
                          value={userRequest.requested_amount} 
                          precision={1}
                        /> kWh
                      </span>
                  </div>
                  <Progress 
                    value={(userRequest.current_amount / userRequest.requested_amount) * 100} 
                    className="h-2"
                  />
                  </motion.div>
              )}
            </CardContent>
          </Card>
          </motion.div>
        )}

        {/* 如果没有活跃请求且已检查过，显示提示 */}
        {!userRequest && hasCheckedUserRequest && (
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
          <Card className="mb-6 border-dashed">
            <CardContent className="pt-6">
              <div className="text-center">
                  <motion.div
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                <AlertCircle className="mx-auto h-12 w-12 text-gray-400" />
                  </motion.div>
                  <motion.h3 
                    className="mt-2 text-sm font-medium text-gray-900 dark:text-white"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4 }}
                  >
                    暂无活跃的充电请求
                  </motion.h3>
                  <motion.p 
                    className="mt-1 text-sm text-gray-500 dark:text-gray-400"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                  >
                  您当前没有进行中的充电请求
                  </motion.p>
                  <motion.div 
                    className="mt-6"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.6, type: "spring", stiffness: 200 }}
                  >
                    <ChargingRequestDialog
                      vehicles={vehicles}
                      systemParams={systemParams}
                      queueStatus={queueStatus}
                      onRequestSubmitted={handleRequestUpdate}
                      activeRequests={activeRequests}
                    />
                  </motion.div>
              </div>
            </CardContent>
          </Card>
          </motion.div>
        )}

        {/* 统计卡片 */}
        <motion.div 
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.div variants={itemVariants}>
            <Card className="hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">快充桩队列</CardTitle>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                >
              <Zap className="h-4 w-4 text-muted-foreground" />
                </motion.div>
            </CardHeader>
            <CardContent>
                <motion.div 
                  className="text-2xl font-bold text-gray-900 dark:text-white"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.5, delay: 0.4 }}
                >
                  <AnimatedNumber value={queueStatus?.pile_queues?.fast?.total_count || 0} />
                </motion.div>
              <p className="text-xs text-muted-foreground">
                等待: {queueStatus?.pile_queues?.fast?.waiting_count || 0} | 
                充电: {queueStatus?.pile_queues?.fast?.charging_count || 0}
              </p>
            </CardContent>
          </Card>
          </motion.div>

          <motion.div variants={itemVariants}>
            <Card className="hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">慢充桩队列</CardTitle>
              <Battery className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
                <motion.div 
                  className="text-2xl font-bold text-gray-900 dark:text-white"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.5, delay: 0.5 }}
                >
                  <AnimatedNumber value={queueStatus?.pile_queues?.slow?.total_count || 0} />
                </motion.div>
              <p className="text-xs text-muted-foreground">
                等待: {queueStatus?.pile_queues?.slow?.waiting_count || 0} | 
                充电: {queueStatus?.pile_queues?.slow?.charging_count || 0}
              </p>
            </CardContent>
          </Card>
          </motion.div>

          <motion.div variants={itemVariants}>
            <Card className="hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">外部等候区</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
                <motion.div 
                  className="text-2xl font-bold text-gray-900 dark:text-white"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.5, delay: 0.6 }}
                >
                  <AnimatedNumber value={queueStatus?.external_queue?.total_count || 0} />
                </motion.div>
              <p className="text-xs text-muted-foreground">
                快充: {queueStatus?.external_queue?.fast_count || 0} 人 | 
                慢充: {queueStatus?.external_queue?.slow_count || 0} 人
              </p>
            </CardContent>
          </Card>
          </motion.div>

          <motion.div variants={itemVariants}>
            <Card className="hover:shadow-lg transition-shadow duration-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">可用充电桩</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
                <motion.div 
                  className="text-2xl font-bold text-gray-900 dark:text-white"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.5, delay: 0.7 }}
                >
                {pilesStatus ? 
                    [...(pilesStatus.fast_piles || []), ...(pilesStatus.slow_piles || [])]
                    .filter(pile => pile.status === 'normal' && !pile.is_working).length 
                  : 0
                }
                </motion.div>
              <p className="text-xs text-muted-foreground">空闲充电桩</p>
            </CardContent>
          </Card>
          </motion.div>
        </motion.div>

        {/* 详细信息标签页 */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
        >
        <Tabs defaultValue="piles" className="space-y-4">
          <TabsList>
            <TabsTrigger value="piles">充电桩状态</TabsTrigger>
            <TabsTrigger value="queue">排队详情</TabsTrigger>
            <TabsTrigger value="request">发起充电</TabsTrigger>
          </TabsList>

          <TabsContent value="piles" className="space-y-4">
              <motion.div 
                className="grid grid-cols-1 md:grid-cols-2 gap-6"
                variants={containerVariants}
                initial="hidden"
                animate="visible"
              >
                <motion.div variants={itemVariants}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Zap className="mr-2 h-5 w-5 text-blue-600 dark:text-blue-400" />
                    快充桩状态
                  </CardTitle>
                </CardHeader>
                <CardContent>
                      <motion.div 
                        className="space-y-2"
                        variants={containerVariants}
                        initial="hidden"
                        animate="visible"
                      >
                        {pilesStatus?.fast_piles?.map((pile, index) => (
                          <motion.div 
                            key={pile.pile_id} 
                            className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800/50 rounded"
                            variants={itemVariants}
                            whileHover={{ scale: 1.02, backgroundColor: "rgba(59, 130, 246, 0.1)" }}
                            transition={{ duration: 0.2 }}
                          >
                        <span className="font-medium text-gray-900 dark:text-white">{pile.pile_id}</span>
                        <div className="flex items-center space-x-2">
                          <Badge variant={pile.is_working ? 'destructive' : 'secondary'}>
                            {pile.is_working ? `使用中 (${pile.current_user})` : '空闲'}
                          </Badge>
                          <Badge variant={pile.status === 'normal' ? 'default' : 'destructive'}>
                            {pile.status === 'normal' ? '正常' : '故障'}
                          </Badge>
                        </div>
                          </motion.div>
                    ))}
                      </motion.div>
                </CardContent>
              </Card>
                </motion.div>

                <motion.div variants={itemVariants}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Battery className="mr-2 h-5 w-5 text-green-600 dark:text-green-400" />
                    慢充桩状态
                  </CardTitle>
                </CardHeader>
                <CardContent>
                      <motion.div 
                        className="space-y-2"
                        variants={containerVariants}
                        initial="hidden"
                        animate="visible"
                      >
                        {pilesStatus?.slow_piles?.map((pile, index) => (
                          <motion.div 
                            key={pile.pile_id} 
                            className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800/50 rounded"
                            variants={itemVariants}
                            whileHover={{ scale: 1.02, backgroundColor: "rgba(34, 197, 94, 0.1)" }}
                            transition={{ duration: 0.2 }}
                          >
                        <span className="font-medium text-gray-900 dark:text-white">{pile.pile_id}</span>
                        <div className="flex items-center space-x-2">
                          <Badge variant={pile.is_working ? 'destructive' : 'secondary'}>
                            {pile.is_working ? `使用中 (${pile.current_user})` : '空闲'}
                          </Badge>
                          <Badge variant={pile.status === 'normal' ? 'default' : 'destructive'}>
                            {pile.status === 'normal' ? '正常' : '故障'}
                          </Badge>
                        </div>
                          </motion.div>
                    ))}
                      </motion.div>
                </CardContent>
              </Card>
                </motion.div>
              </motion.div>
          </TabsContent>

          <TabsContent value="queue" className="space-y-4">
            {/* 外部等候区 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Users className="mr-2 h-5 w-5 text-purple-600 dark:text-purple-400" />
                  🚪 外部等候区
                </CardTitle>
                <CardDescription>
                  当前有 {queueStatus?.external_queue?.total_count || 0} 人在外部等候区等待
                  （快充: {queueStatus?.external_queue?.fast_count || 0} 人，慢充: {queueStatus?.external_queue?.slow_count || 0} 人）
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {queueStatus?.external_queue?.requests?.length > 0 ? (
                    queueStatus.external_queue.requests.map((item) => (
                      <div key={item.queue_number} className="flex items-center justify-between p-3 bg-purple-50 dark:bg-purple-900/20 rounded border border-purple-200 dark:border-purple-700">
                        <div className="flex items-center space-x-3">
                          <Badge variant="outline" className="border-purple-300 text-purple-700 dark:text-purple-300">
                            #{item.queue_position}
                          </Badge>
                          <span className="font-medium text-gray-900 dark:text-white">{item.queue_number}</span>
                          <Badge variant={item.charging_mode === 'fast' ? 'default' : 'secondary'}>
                            {item.charging_mode === 'fast' ? '快充' : '慢充'}
                          </Badge>
                        </div>
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          预计等待 {item.estimated_wait_time} 分钟
                        </span>
                      </div>
                    ))
                  ) : (
                    <p className="text-center text-gray-500 dark:text-gray-400 py-4">外部等候区暂无排队用户</p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* 桩队列 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Zap className="mr-2 h-5 w-5 text-blue-600 dark:text-blue-400" />
                    🔌 快充桩队列
                  </CardTitle>
                  <CardDescription>
                    桩队列有 {queueStatus?.pile_queues?.fast?.waiting_count || 0} 人等待，
                    {queueStatus?.pile_queues?.fast?.charging_count || 0} 人正在充电
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {queueStatus?.pile_queues?.fast?.requests?.length > 0 ? (
                      queueStatus.pile_queues.fast.requests.map((item) => (
                        <div key={item.queue_number} className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-700">
                          <div className="flex items-center space-x-3">
                            <Badge variant="outline" className="border-blue-300 text-blue-700 dark:text-blue-300">
                              #{item.queue_position}
                            </Badge>
                            <span className="font-medium text-gray-900 dark:text-white">{item.queue_number}</span>
                            <Badge variant={item.status === 'charging' ? 'default' : 'secondary'}>
                              {item.status === 'charging' ? '充电中' : '等待中'}
                            </Badge>
                            {item.pile_id && (
                              <Badge variant="outline">{item.pile_id}</Badge>
                            )}
                          </div>
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            {item.estimated_wait_time > 0 ? `预计等待 ${item.estimated_wait_time} 分钟` : '正在充电'}
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="text-center text-gray-500 dark:text-gray-400 py-4">快充桩队列暂无用户</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Battery className="mr-2 h-5 w-5 text-green-600 dark:text-green-400" />
                    🔌 慢充桩队列
                  </CardTitle>
                  <CardDescription>
                    桩队列有 {queueStatus?.pile_queues?.slow?.waiting_count || 0} 人等待，
                    {queueStatus?.pile_queues?.slow?.charging_count || 0} 人正在充电
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {queueStatus?.pile_queues?.slow?.requests?.length > 0 ? (
                      queueStatus.pile_queues.slow.requests.map((item) => (
                        <div key={item.queue_number} className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-700">
                          <div className="flex items-center space-x-3">
                            <Badge variant="outline" className="border-green-300 text-green-700 dark:text-green-300">
                              #{item.queue_position}
                            </Badge>
                            <span className="font-medium text-gray-900 dark:text-white">{item.queue_number}</span>
                            <Badge variant={item.status === 'charging' ? 'default' : 'secondary'}>
                              {item.status === 'charging' ? '充电中' : '等待中'}
                            </Badge>
                            {item.pile_id && (
                              <Badge variant="outline">{item.pile_id}</Badge>
                            )}
                          </div>
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            {item.estimated_wait_time > 0 ? `预计等待 ${item.estimated_wait_time} 分钟` : '正在充电'}
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="text-center text-gray-500 dark:text-gray-400 py-4">慢充桩队列暂无用户</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="request" className="space-y-4">
            {!userRequest ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                >
              <Card>
                <CardHeader>
                  <CardTitle>发起充电请求</CardTitle>
                  <CardDescription>
                    选择充电模式并提交充电请求
                  </CardDescription>
                </CardHeader>
                <CardContent>
                      <ChargingRequestDialog
                        vehicles={vehicles}
                        systemParams={systemParams}
                        queueStatus={queueStatus}
                        onRequestSubmitted={handleRequestUpdate}
                        activeRequests={activeRequests}
                      />
                </CardContent>
              </Card>
                </motion.div>
            ) : (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                >
              <Card>
                <CardHeader>
                  <CardTitle>当前有活跃的充电请求</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600 dark:text-gray-400 mb-4">
                    您已有一个进行中的充电请求，请等待完成后再发起新的请求。
                  </p>
                  <Button 
                    variant="outline" 
                        onClick={() => {
                          toast.info('请切换到"发起充电"选项卡查看充电详情');
                        }}
                  >
                    查看详情
                  </Button>
                </CardContent>
              </Card>
                </motion.div>
            )}
          </TabsContent>
        </Tabs>
        </motion.div>
      </div>
    </PageTransition>
  );
}
