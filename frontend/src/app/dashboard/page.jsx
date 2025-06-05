'use client';

import { useState, useEffect } from 'react';
import Layout from '@/components/layout/Layout';
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

export default function DashboardPage() {
  const [queueStatus, setQueueStatus] = useState(null);
  const [pilesStatus, setPilesStatus] = useState(null);
  const [userRequest, setUserRequest] = useState(null);
  const [hasCheckedUserRequest, setHasCheckedUserRequest] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    // 每30秒刷新系统状态数据
    const interval = setInterval(fetchSystemStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // 系统状态轮询（不包含用户请求）
  const fetchSystemStatus = async () => {
    try {
      const [queueData, pilesData] = await Promise.all([
        chargingAPI.getQueueStatus(),
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
    }, 15000); // 用户状态轮询间隔更短（15秒）

    // 组件卸载时清理
    return () => clearInterval(userInterval);
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

  return (
    <Layout>
      <div className="px-4 py-6 sm:px-0">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">充电站仪表板</h1>
          <p className="mt-2 text-gray-600 dark:text-gray-300">实时监控充电站状态和您的充电请求</p>
        </div>

        {/* 用户当前请求状态 */}
        {userRequest && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center">
                <Zap className="mr-2 h-5 w-5 text-blue-600 dark:text-blue-400" />
                您的充电状态
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">队列号</p>
                  <p className="text-lg font-semibold text-gray-900 dark:text-white">{userRequest.queue_number}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">当前状态</p>
                  <Badge variant={userRequest.current_status === 'charging' ? 'default' : 'secondary'}>
                    {userRequest.current_status === 'waiting' ? '等待中' : 
                     userRequest.current_status === 'charging' ? '充电中' : '已完成'}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">预计等待时间</p>
                  <p className="text-lg font-semibold text-gray-900 dark:text-white">{userRequest.estimated_wait_time} 分钟</p>
                </div>
              </div>
              
              {userRequest.current_status === 'charging' && (
                <div className="mt-4">
                  <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
                    <span>充电进度</span>
                    <span>{userRequest.current_amount} / {userRequest.requested_amount} kWh</span>
                  </div>
                  <Progress 
                    value={(userRequest.current_amount / userRequest.requested_amount) * 100} 
                    className="h-2"
                  />
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* 如果没有活跃请求且已检查过，显示提示 */}
        {!userRequest && hasCheckedUserRequest && (
          <Card className="mb-6 border-dashed">
            <CardContent className="pt-6">
              <div className="text-center">
                <AlertCircle className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">暂无活跃的充电请求</h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  您当前没有进行中的充电请求
                </p>
                <div className="mt-6">
                  <Button onClick={() => window.location.href = '/charging/'}>
                    发起充电请求
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">快充排队</CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {queueStatus?.fast_charging?.waiting_count || 0}
              </div>
              <p className="text-xs text-muted-foreground">人正在等待</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">慢充排队</CardTitle>
              <Battery className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {queueStatus?.slow_charging?.waiting_count || 0}
              </div>
              <p className="text-xs text-muted-foreground">人正在等待</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">等候区状态</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {queueStatus?.waiting_area_capacity?.current || 0}/
                {queueStatus?.waiting_area_capacity?.max || 10}
              </div>
              <p className="text-xs text-muted-foreground">当前/最大容量</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">可用充电桩</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {pilesStatus ? 
                  [...pilesStatus.fast_piles, ...pilesStatus.slow_piles]
                    .filter(pile => pile.status === 'normal' && !pile.is_working).length 
                  : 0
                }
              </div>
              <p className="text-xs text-muted-foreground">空闲充电桩</p>
            </CardContent>
          </Card>
        </div>

        {/* 详细信息标签页 */}
        <Tabs defaultValue="piles" className="space-y-4">
          <TabsList>
            <TabsTrigger value="piles">充电桩状态</TabsTrigger>
            <TabsTrigger value="queue">排队详情</TabsTrigger>
            <TabsTrigger value="request">发起充电</TabsTrigger>
          </TabsList>

          <TabsContent value="piles" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Zap className="mr-2 h-5 w-5 text-blue-600 dark:text-blue-400" />
                    快充桩状态
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {pilesStatus?.fast_piles?.map((pile) => (
                      <div key={pile.pile_id} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800/50 rounded">
                        <span className="font-medium text-gray-900 dark:text-white">{pile.pile_id}</span>
                        <div className="flex items-center space-x-2">
                          <Badge variant={pile.is_working ? 'destructive' : 'secondary'}>
                            {pile.is_working ? `使用中 (${pile.current_user})` : '空闲'}
                          </Badge>
                          <Badge variant={pile.status === 'normal' ? 'default' : 'destructive'}>
                            {pile.status === 'normal' ? '正常' : '故障'}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Battery className="mr-2 h-5 w-5 text-green-600 dark:text-green-400" />
                    慢充桩状态
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {pilesStatus?.slow_piles?.map((pile) => (
                      <div key={pile.pile_id} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800/50 rounded">
                        <span className="font-medium text-gray-900 dark:text-white">{pile.pile_id}</span>
                        <div className="flex items-center space-x-2">
                          <Badge variant={pile.is_working ? 'destructive' : 'secondary'}>
                            {pile.is_working ? `使用中 (${pile.current_user})` : '空闲'}
                          </Badge>
                          <Badge variant={pile.status === 'normal' ? 'default' : 'destructive'}>
                            {pile.status === 'normal' ? '正常' : '故障'}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="queue" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Zap className="mr-2 h-5 w-5 text-blue-600 dark:text-blue-400" />
                    快充排队详情
                  </CardTitle>
                  <CardDescription>
                    当前有 {queueStatus?.fast_charging?.waiting_count || 0} 人等待快充
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {queueStatus?.fast_charging?.queue_list?.length > 0 ? (
                      queueStatus.fast_charging.queue_list.map((item, index) => (
                        <div key={item.queue_number} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded">
                          <div className="flex items-center space-x-3">
                            <Badge variant="outline">#{index + 1}</Badge>
                            <span className="font-medium text-gray-900 dark:text-white">{item.queue_number}</span>
                          </div>
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            预计等待 {item.estimated_wait_time} 分钟
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="text-center text-gray-500 dark:text-gray-400 py-4">暂无排队用户</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Battery className="mr-2 h-5 w-5 text-green-600 dark:text-green-400" />
                    慢充排队详情
                  </CardTitle>
                  <CardDescription>
                    当前有 {queueStatus?.slow_charging?.waiting_count || 0} 人等待慢充
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {queueStatus?.slow_charging?.queue_list?.length > 0 ? (
                      queueStatus.slow_charging.queue_list.map((item, index) => (
                        <div key={item.queue_number} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded">
                          <div className="flex items-center space-x-3">
                            <Badge variant="outline">#{index + 1}</Badge>
                            <span className="font-medium text-gray-900 dark:text-white">{item.queue_number}</span>
                          </div>
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            预计等待 {item.estimated_wait_time} 分钟
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="text-center text-gray-500 dark:text-gray-400 py-4">暂无排队用户</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="request" className="space-y-4">
            {!userRequest ? (
              <Card>
                <CardHeader>
                  <CardTitle>发起充电请求</CardTitle>
                  <CardDescription>
                    选择充电模式并提交充电请求
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button onClick={() => window.location.href = '/charging/'}>
                    发起充电请求
                  </Button>
                </CardContent>
              </Card>
            ) : (
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
                    onClick={() => window.location.href = '/charging/'}
                  >
                    查看详情
                  </Button>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
