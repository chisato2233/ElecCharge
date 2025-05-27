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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    // 每30秒刷新一次数据
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [queueData, pilesData] = await Promise.all([
        chargingAPI.getQueueStatus(),
        chargingAPI.getPilesStatus()
      ]);

      setQueueStatus(queueData.data);
      setPilesStatus(pilesData.data);

      // 尝试获取用户当前请求状态
      try {
        const requestData = await chargingAPI.getRequestStatus();
        setUserRequest(requestData.data);
      } catch (error) {
        // 用户没有活跃请求
        setUserRequest(null);
      }
    } catch (error) {
      console.error('获取数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">加载中...</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="px-4 py-6 sm:px-0">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">充电站仪表板</h1>
          <p className="mt-2 text-gray-600">实时监控充电站状态和您的充电请求</p>
        </div>

        {/* 用户当前请求状态 */}
        {userRequest && (
          <Card className="mb-6 border-blue-200 bg-blue-50">
            <CardHeader>
              <CardTitle className="flex items-center">
                <Zap className="mr-2 h-5 w-5 text-blue-600" />
                您的充电状态
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-gray-600">队列号</p>
                  <p className="text-lg font-semibold">{userRequest.queue_number}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">当前状态</p>
                  <Badge variant={userRequest.current_status === 'charging' ? 'default' : 'secondary'}>
                    {userRequest.current_status === 'waiting' ? '等待中' : 
                     userRequest.current_status === 'charging' ? '充电中' : '已完成'}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm text-gray-600">预计等待时间</p>
                  <p className="text-lg font-semibold">{userRequest.estimated_wait_time} 分钟</p>
                </div>
              </div>
              
              {userRequest.current_status === 'charging' && (
                <div className="mt-4">
                  <div className="flex justify-between text-sm text-gray-600 mb-2">
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

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">快充排队</CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
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
              <div className="text-2xl font-bold">
                {queueStatus?.slow_charging?.waiting_count || 0}
              </div>
              <p className="text-xs text-muted-foreground">人正在等待</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">等候区</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {queueStatus?.waiting_area_capacity?.current || 0} / {queueStatus?.waiting_area_capacity?.max || 0}
              </div>
              <p className="text-xs text-muted-foreground">当前容量</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">可用充电桩</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
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
              {/* 快充桩 */}
              <Card>
                <CardHeader>
                  <CardTitle>快充桩状态</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {pilesStatus?.fast_piles?.map((pile) => (
                      <div key={pile.pile_id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <p className="font-medium">{pile.pile_id}</p>
                          <p className="text-sm text-gray-600">
                            {pile.current_user || '空闲'}
                          </p>
                        </div>
                        <Badge variant={
                          pile.status === 'normal' ? 
                            (pile.is_working ? 'default' : 'secondary') : 
                            'destructive'
                        }>
                          {pile.status === 'normal' ? 
                            (pile.is_working ? '使用中' : '空闲') : 
                            '故障'
                          }
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* 慢充桩 */}
              <Card>
                <CardHeader>
                  <CardTitle>慢充桩状态</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {pilesStatus?.slow_piles?.map((pile) => (
                      <div key={pile.pile_id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <p className="font-medium">{pile.pile_id}</p>
                          <p className="text-sm text-gray-600">
                            {pile.current_user || '空闲'}
                          </p>
                        </div>
                        <Badge variant={
                          pile.status === 'normal' ? 
                            (pile.is_working ? 'default' : 'secondary') : 
                            'destructive'
                        }>
                          {pile.status === 'normal' ? 
                            (pile.is_working ? '使用中' : '空闲') : 
                            '故障'
                          }
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="queue" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* 快充排队 */}
              <Card>
                <CardHeader>
                  <CardTitle>快充排队列表</CardTitle>
                  <CardDescription>
                    当前有 {queueStatus?.fast_charging?.waiting_count || 0} 人排队
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {queueStatus?.fast_charging?.queue_list?.length > 0 ? (
                    <div className="space-y-2">
                      {queueStatus.fast_charging.queue_list.map((item, index) => (
                        <div key={item.queue_number} className="flex items-center justify-between p-2 border rounded">
                          <span className="font-medium">{item.queue_number}</span>
                          <span className="text-sm text-gray-600">
                            预计 {item.estimated_wait_time} 分钟
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">暂无排队</p>
                  )}
                </CardContent>
              </Card>

              {/* 慢充排队 */}
              <Card>
                <CardHeader>
                  <CardTitle>慢充排队列表</CardTitle>
                  <CardDescription>
                    当前有 {queueStatus?.slow_charging?.waiting_count || 0} 人排队
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {queueStatus?.slow_charging?.queue_list?.length > 0 ? (
                    <div className="space-y-2">
                      {queueStatus.slow_charging.queue_list.map((item, index) => (
                        <div key={item.queue_number} className="flex items-center justify-between p-2 border rounded">
                          <span className="font-medium">{item.queue_number}</span>
                          <span className="text-sm text-gray-600">
                            预计 {item.estimated_wait_time} 分钟
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">暂无排队</p>
                  )}
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
                  <Button onClick={() => window.location.href = '/charging/request'}>
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
                  <p className="text-gray-600 mb-4">
                    您已有一个进行中的充电请求，请等待完成后再发起新的请求。
                  </p>
                  <Button 
                    variant="outline" 
                    onClick={() => window.location.href = '/charging/status'}
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
