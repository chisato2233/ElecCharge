'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { vehicleAPI } from '@/lib/vehicles';
import { chargingAPI } from '@/lib/charging';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Zap, Activity, Clock, Users, Battery } from 'lucide-react';

// 导入组件
import ChargingStatusList from './components/ChargingStatusCard';
import ChargingRequestDialog from './components/ChargingRequestDialog';
import { BgAnimateButton } from '@/components/ui/bg-animate-button';
import PageTransition, { cardVariants, containerVariants, itemVariants } from '@/components/layout/PageTransition';
import { AnimatedNumber } from '@/components/ui/AnimatedNumber';

export default function ChargingPage() {
  const [vehicles, setVehicles] = useState([]);
  const [queueStatus, setQueueStatus] = useState(null);
  const [pilesStatus, setPilesStatus] = useState(null);
  const [systemParams, setSystemParams] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeRequests, setActiveRequests] = useState([]);

  useEffect(() => {
    fetchInitialData();
    // 每15秒更新系统状态和用户请求
    const interval = setInterval(async () => {
      await Promise.all([
        fetchStatusData(),
        fetchActiveRequests()
      ]);
    }, 200);
    return () => clearInterval(interval);
  }, []);

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      await Promise.all([
        fetchVehicles(),
        fetchStatusData(),
        fetchSystemParams(),
        fetchActiveRequests()
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

  const handleRequestUpdate = async () => {
    // 当请求状态更新时，重新获取活跃请求列表和状态数据
    await Promise.all([
      fetchActiveRequests(),
      fetchStatusData()
    ]);
  };

  // 触发充电对话框
  const triggerChargingDialog = () => {
    // 查找并点击页面顶部的充电请求按钮
    const chargingButton = document.querySelector('[data-testid="charging-request-button"] button');
    if (chargingButton) {
      chargingButton.click();
    } else {
      toast.info('请点击右上角的"充电请求"按钮开始充电');
    }
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
        <div className="max-w-6xl mx-auto">
          {/* 页面标题和操作区 */}
          <motion.div 
            className="mb-8 flex items-center justify-between"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          >
            <div>
              <motion.h1 
                className="text-3xl font-bold text-gray-900 dark:text-white"
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.1 }}
              >
                充电管理中心
              </motion.h1>
              <motion.p 
                className="mt-2 text-gray-600 dark:text-gray-300"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.2 }}
              >
                智能多级队列 • 精确时间估算 • 实时状态监控
              </motion.p>
            </div>

            {/* 发起充电请求按钮 */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <div data-testid="charging-request-button">
                <ChargingRequestDialog
                  vehicles={vehicles}
                  systemParams={systemParams}
                  queueStatus={queueStatus}
                  onRequestSubmitted={handleRequestUpdate}
                  activeRequests={activeRequests}
                          />
                        </div>
            </motion.div>
          </motion.div>

          {/* 系统状态概览卡片 */}
          <motion.div 
            className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {/* 总充电桩数 */}
            <motion.div variants={itemVariants}>
              <Card className="hover:shadow-lg transition-shadow duration-300">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">总充电桩</CardTitle>
                  <Zap className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <motion.div 
                    className="text-2xl font-bold text-gray-900 dark:text-white"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.5 }}
                  >
                    <AnimatedNumber 
                      value={pilesStatus ? 
                        (pilesStatus.fast_piles?.length || 0) + (pilesStatus.slow_piles?.length || 0) 
                        : 0
                      }
                    />
                  </motion.div>
                  <p className="text-xs text-muted-foreground">
                    {pilesStatus ? 
                      `工作中: ${[...(pilesStatus.fast_piles || []), ...(pilesStatus.slow_piles || [])].filter(p => p.is_working).length}` 
                      : '加载中...'
                    }
                  </p>
              </CardContent>
            </Card>
            </motion.div>

            {/* 快充队列 */}
            <motion.div variants={itemVariants}>
              <Card className="hover:shadow-lg transition-shadow duration-300">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">快充队列</CardTitle>
                  <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                  <motion.div 
                    className="text-2xl font-bold text-gray-900 dark:text-white"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.6 }}
                  >
                    <AnimatedNumber value={queueStatus?.fast_charging?.waiting_count || 0} />
                  </motion.div>
                  <p className="text-xs text-muted-foreground">
                    正在充电: <AnimatedNumber value={queueStatus?.fast_charging?.charging_count || 0} />
                  </p>
              </CardContent>
            </Card>
            </motion.div>

            {/* 慢充队列 */}
            <motion.div variants={itemVariants}>
              <Card className="hover:shadow-lg transition-shadow duration-300">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">慢充队列</CardTitle>
                <Battery className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                  <motion.div 
                    className="text-2xl font-bold text-gray-900 dark:text-white"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.7 }}
                  >
                    <AnimatedNumber value={queueStatus?.slow_charging?.waiting_count || 0} />
                  </motion.div>
                  <p className="text-xs text-muted-foreground">
                    正在充电: <AnimatedNumber value={queueStatus?.slow_charging?.charging_count || 0} />
                  </p>
              </CardContent>
            </Card>
            </motion.div>

            {/* 外部等候区 */}
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
                    transition={{ duration: 0.5, delay: 0.8 }}
                  >
                    <AnimatedNumber value={queueStatus?.external_waiting?.total_count || 0} />
                  </motion.div>
                  <p className="text-xs text-muted-foreground">
                    快充: <AnimatedNumber value={queueStatus?.external_waiting?.fast_count || 0} /> | 
                    慢充: <AnimatedNumber value={queueStatus?.external_waiting?.slow_count || 0} />
                  </p>
              </CardContent>
            </Card>
            </motion.div>
          </motion.div>

          {/* 当前活跃的充电请求 */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            <ChargingStatusList 
              activeRequests={activeRequests}
              onRequestUpdate={handleRequestUpdate}
            />
          </motion.div>

          {/* 如果没有活跃请求，显示提示信息 */}
          {activeRequests.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.5 }}
            >
              <Card className="text-center py-12">
                <CardContent>
                  <div className="flex flex-col items-center space-y-4">
                    <motion.div 
                      className="p-4 bg-gray-100 dark:bg-gray-800 rounded-full"
                      whileHover={{ rotate: 360 }}
                      transition={{ duration: 0.5 }}
                    >
                      <Zap className="h-8 w-8 text-gray-400" />
                    </motion.div>
                    <div>
                      <motion.h3 
                        className="text-lg font-semibold text-gray-900 dark:text-white mb-2"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.6 }}
                      >
                        暂无活跃的充电请求
                      </motion.h3>
                      <motion.p 
                        className="text-gray-600 dark:text-gray-400 mb-4"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.7 }}
                      >
                        点击右上角的"充电请求"按钮开始充电
                      </motion.p>
                      <motion.div 
                        className="flex flex-wrap justify-center gap-2"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.8 }}
                      >
                        <Badge variant="outline" className="text-xs">
                          <Clock className="mr-1 h-3 w-3" />
                          智能排队
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          <Activity className="mr-1 h-3 w-3" />
                          实时监控
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          <Zap className="mr-1 h-3 w-3" />
                          快速充电
                        </Badge>
                      </motion.div>
                      <motion.div 
                        className="mt-6"
                        initial={{ opacity: 0, scale: 0.5 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.9, type: "spring", stiffness: 200 }}
                      >
                        <BgAnimateButton 
                          gradient="nebula"
                          animation="pulse"
                          shadow="soft"
                          rounded="xl"
                          className="transition-transform hover:scale-105"
                          onClick={triggerChargingDialog}
                        >
                          <div className="flex items-center justify-center">
                          <Zap className="mr-2 h-4 w-4" />
                            立即开始新的充电请求
                          </div>
                        </BgAnimateButton>
                      </motion.div>
                    </div>
                  </div>
            </CardContent>
          </Card>
            </motion.div>
          )}
        </div>
      </div>
    </PageTransition>
  );
} 