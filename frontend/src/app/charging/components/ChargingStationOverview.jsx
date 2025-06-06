'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Zap, Battery, Users, Clock, AlertCircle } from 'lucide-react';
import { useState, useEffect } from 'react';
import { chargingAPI } from '@/lib/charging';

function PileStatusCard({ pile, title, icon: Icon, color = "blue" }) {
  const getStatusBadge = (isWorking, estimatedTime) => {
    if (isWorking) {
      return (
        <Badge variant="outline" className="text-xs">
          <Zap className="h-3 w-3 mr-1" />
          充电中 ({estimatedTime}分钟)
        </Badge>
      );
    } else {
      return (
        <Badge variant="secondary" className="text-xs">
          空闲
        </Badge>
      );
    }
  };

  return (
    <div className="border rounded-lg p-3 space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-sm font-medium">{pile.pile_id}</span>
        {getStatusBadge(pile.is_working, pile.estimated_remaining_time)}
      </div>
      
      {pile.current_charging?.queue_number && (
        <div className="text-xs text-gray-600 dark:text-gray-400">
          充电中: {pile.current_charging.queue_number}
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 mt-1">
            <div 
              className="bg-green-500 h-1.5 rounded-full" 
              style={{ width: `${pile.current_charging.progress}%` }}
            ></div>
          </div>
        </div>
      )}
      
      <div className="flex justify-between items-center text-xs">
        <span className="text-gray-600 dark:text-gray-400">队列:</span>
        <span className={`font-medium ${pile.queue_count >= pile.max_queue_size ? 'text-red-600' : 'text-gray-900 dark:text-white'}`}>
          {pile.queue_count}/{pile.max_queue_size}
        </span>
      </div>
      
      {pile.queue_list && pile.queue_list.length > 0 && (
        <div className="space-y-1">
          <div className="text-xs text-gray-600 dark:text-gray-400">等待队列:</div>
          {pile.queue_list.slice(0, 2).map((request, index) => (
            <div key={index} className="text-xs bg-gray-50 dark:bg-gray-800 rounded px-2 py-1">
              <div className="flex justify-between">
                <span>{request.queue_number}</span>
                <span className="text-gray-500">第{request.position}位</span>
              </div>
            </div>
          ))}
          {pile.queue_list.length > 2 && (
            <div className="text-xs text-gray-500 text-center">
              还有 {pile.queue_list.length - 2} 个请求...
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ChargingStationOverview({ queueStatus, pilesStatus }) {
  const [enhancedData, setEnhancedData] = useState(null);
  const [loading, setLoading] = useState(false);

  // 获取增强的队列状态数据
  useEffect(() => {
    const fetchEnhancedData = async () => {
      try {
        setLoading(true);
        const response = await chargingAPI.getEnhancedQueueStatus();
        if (response.success) {
          setEnhancedData(response.data);
        }
      } catch (error) {
        console.error('获取增强队列状态失败:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchEnhancedData();
    
    // 每30秒更新一次
    const interval = setInterval(fetchEnhancedData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !enhancedData) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {[1, 2, 3].map(i => (
          <Card key={i} className="animate-pulse">
            <CardContent className="p-6">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
              <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const fastData = enhancedData?.fast || {};
  const slowData = enhancedData?.slow || {};

  return (
    <div className="space-y-6 mb-8">
      {/* 总览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">快充桩状态</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {fastData.piles?.filter(p => !p.is_working).length || 0}
              /
              {fastData.piles?.length || 0}
            </div>
            <p className="text-xs text-muted-foreground">可用/总数</p>
            <div className="mt-2 space-y-1">
              <Badge variant="secondary" className="text-xs">
                外部等候: {fastData.external_waiting?.count || 0}人
              </Badge>
              <Badge variant="outline" className="text-xs">
                总等待: {fastData.total_waiting || 0}人
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
              {slowData.piles?.filter(p => !p.is_working).length || 0}
              /
              {slowData.piles?.length || 0}
            </div>
            <p className="text-xs text-muted-foreground">可用/总数</p>
            <div className="mt-2 space-y-1">
              <Badge variant="secondary" className="text-xs">
                外部等候: {slowData.external_waiting?.count || 0}人
              </Badge>
              <Badge variant="outline" className="text-xs">
                总等待: {slowData.total_waiting || 0}人
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">外部等候区</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {(fastData.external_waiting?.count || 0) + (slowData.external_waiting?.count || 0)}
              /
              {queueStatus?.waiting_area_capacity?.max || 20}
            </div>
            <p className="text-xs text-muted-foreground">当前/容量</p>
            <div className="mt-2">
              <Progress 
                value={queueStatus?.waiting_area_capacity ? 
                  (queueStatus.waiting_area_capacity.current / queueStatus.waiting_area_capacity.max) * 100 : 
                  (((fastData.external_waiting?.count || 0) + (slowData.external_waiting?.count || 0)) / 20) * 100
                } 
                className="h-2"
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 详细桩状态 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 快充桩详情 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Zap className="mr-2 h-5 w-5" />
              快充桩详情
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {fastData.external_waiting && fastData.external_waiting.count > 0 && (
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                  <div className="flex items-center text-amber-800 dark:text-amber-200">
                    <Clock className="h-4 w-4 mr-2" />
                    <span className="text-sm font-medium">
                      外部等候区: {fastData.external_waiting.count} 人等待
                    </span>
                  </div>
                  {fastData.external_waiting.queue_list && fastData.external_waiting.queue_list.length > 0 && (
                    <div className="mt-2 text-xs text-amber-700 dark:text-amber-300">
                      前5位: {fastData.external_waiting.queue_list.slice(0, 5).map(q => q.queue_number).join(', ')}
                    </div>
                  )}
                </div>
              )}

              <div className="grid grid-cols-1 gap-3">
                {fastData.piles?.map((pile) => (
                  <PileStatusCard
                    key={pile.pile_id}
                    pile={pile}
                    title={pile.pile_id}
                    icon={Zap}
                    color="blue"
                  />
                )) || (
                  <div className="text-center text-gray-500 py-4">
                    暂无快充桩信息
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 慢充桩详情 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Battery className="mr-2 h-5 w-5" />
              慢充桩详情
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {slowData.external_waiting && slowData.external_waiting.count > 0 && (
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                  <div className="flex items-center text-amber-800 dark:text-amber-200">
                    <Clock className="h-4 w-4 mr-2" />
                    <span className="text-sm font-medium">
                      外部等候区: {slowData.external_waiting.count} 人等待
                    </span>
                  </div>
                  {slowData.external_waiting.queue_list && slowData.external_waiting.queue_list.length > 0 && (
                    <div className="mt-2 text-xs text-amber-700 dark:text-amber-300">
                      前5位: {slowData.external_waiting.queue_list.slice(0, 5).map(q => q.queue_number).join(', ')}
                    </div>
                  )}
                </div>
              )}

              <div className="grid grid-cols-1 gap-3">
                {slowData.piles?.map((pile) => (
                  <PileStatusCard
                    key={pile.pile_id}
                    pile={pile}
                    title={pile.pile_id}
                    icon={Battery}
                    color="green"
                  />
                )) || (
                  <div className="text-center text-gray-500 py-4">
                    暂无慢充桩信息
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
} 