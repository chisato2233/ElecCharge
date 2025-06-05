'use client';

import { useState, useEffect } from 'react';
import Layout from '@/components/layout/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Progress } from '@/components/ui/progress';
import { 
  History, 
  Filter, 
  Download, 
  Calendar,
  Zap,
  Battery,
  TrendingUp,
  Clock,
  DollarSign,
  BarChart3,
  PieChart,
  Activity,
  MoreHorizontal,
  FileDown,
  Search,
  SortAsc,
  SortDesc,
  RefreshCw
} from 'lucide-react';
import { chargingAPI } from '@/lib/charging';
import { toast } from 'sonner';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

export default function HistoryPage() {
  const [historyData, setHistoryData] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('records');
  
  // 筛选参数
  const [filters, setFilters] = useState({
    pile_type: 'all',
    start_date: '',
    end_date: '',
    min_amount: '',
    max_amount: '',
    min_cost: '',
    max_cost: '',
    order_by: '-start_time'
  });
  
  // 分页参数
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 10,
    totalCount: 0,
    totalPages: 0,
    next: null,
    previous: null
  });
  
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    fetchData();
  }, [filters, pagination.page]);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // 处理筛选参数，将 'all' 转换为空字符串
      const apiFilters = {
        ...filters,
        pile_type: filters.pile_type === 'all' ? '' : filters.pile_type,
        page: pagination.page,
        page_size: pagination.pageSize
      };
      
      // 并行获取数据
      const promises = [
        chargingAPI.getChargingHistory(apiFilters),
        chargingAPI.getChargingSummary()
      ];
      
      if (activeTab === 'statistics') {
        promises.push(chargingAPI.getChargingStatistics(30));
      }
      
      const [historyResponseData, summaryResponse, statisticsResponse] = await Promise.all(promises);
      
      // 处理Django REST framework的标准分页格式
      if (historyResponseData) {
        console.log('History response:', historyResponseData);
        
        // Django标准分页格式：{count, next, previous, results}
        const historyData = historyResponseData.results || [];
        setHistoryData(historyData);
        
        // 计算分页信息
        const totalCount = historyResponseData.count || 0;
        const pageSize = pagination.pageSize;
        const totalPages = Math.ceil(totalCount / pageSize);
        
        setPagination(prev => ({
          ...prev,
          totalCount,
          totalPages,
          next: historyResponseData.next,
          previous: historyResponseData.previous
        }));
      }
      
      if (summaryResponse.success) {
        setSummary(summaryResponse.data);
      }
      
      if (statisticsResponse && statisticsResponse.success) {
        setStatistics(statisticsResponse.data);
      }
      
    } catch (error) {
      console.error('获取历史数据失败:', error);
      toast.error('获取历史数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchStatistics = async (days = 30) => {
    try {
      const response = await chargingAPI.getChargingStatistics(days);
      if (response.success) {
        setStatistics(response.data);
      }
    } catch (error) {
      console.error('获取统计数据失败:', error);
      toast.error('获取统计数据失败');
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const clearFilters = () => {
    setFilters({
      pile_type: 'all',
      start_date: '',
      end_date: '',
      min_amount: '',
      max_amount: '',
      min_cost: '',
      max_cost: '',
      order_by: '-start_time'
    });
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const handleExport = async () => {
    try {
      setExporting(true);
      
      // 使用与fetchData相同的参数处理逻辑
      const exportFilters = {
        ...filters,
        pile_type: filters.pile_type === 'all' ? '' : filters.pile_type
      };
      
      const response = await chargingAPI.exportChargingHistory(exportFilters);
      
      // 创建下载链接
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `charging_history_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success('导出成功');
    } catch (error) {
      console.error('导出失败:', error);
      toast.error('导出失败');
    } finally {
      setExporting(false);
    }
  };

  const formatCurrency = (amount) => {
    return `¥${parseFloat(amount).toFixed(2)}`;
  };

  const formatDuration = (hours) => {
    if (hours < 1) {
      const minutes = Math.round(hours * 60);
      return `${minutes}分钟`;
    } else if (hours < 24) {
      const wholeHours = Math.floor(hours);
      const remainingMinutes = Math.round((hours - wholeHours) * 60);
      if (remainingMinutes === 0) {
        return `${wholeHours}小时`;
      } else {
        return `${wholeHours}小时${remainingMinutes}分钟`;
      }
    } else {
      const days = Math.floor(hours / 24);
      const remainingHours = Math.floor(hours % 24);
      if (remainingHours === 0) {
        return `${days}天`;
      } else {
        return `${days}天${remainingHours}小时`;
      }
    }
  };

  if (loading && activeTab === 'records') {
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
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center">
            <History className="mr-3 h-8 w-8" />
            充电记录
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-300">查看您的历史充电记录和统计分析</p>
        </div>

        {/* 概要卡片 */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">总充电次数</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {summary.total_sessions}
                </div>
                <p className="text-xs text-muted-foreground">
                  近30天：{summary.recent_sessions}次
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">总充电量</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {summary.summary.total_amount.toFixed(1)} kWh
                </div>
                <p className="text-xs text-muted-foreground">
                  平均每次：{(summary.summary.total_amount / Math.max(summary.total_sessions, 1)).toFixed(1)} kWh
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">总费用</CardTitle>
                <DollarSign className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {formatCurrency(summary.summary.total_cost)}
                </div>
                <p className="text-xs text-muted-foreground">
                  平均每次：{formatCurrency(summary.summary.avg_cost_per_session)}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">活跃度</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  <Badge variant={
                    summary.summary.activity_level === 'very_active' ? 'default' :
                    summary.summary.activity_level === 'active' ? 'secondary' : 'outline'
                  }>
                    {summary.summary.activity_level === 'very_active' ? '非常活跃' :
                     summary.summary.activity_level === 'active' ? '活跃' :
                     summary.summary.activity_level === 'moderate' ? '一般' : '不活跃'}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  常用：{summary.summary.most_used_mode || '无'}
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList>
            <TabsTrigger value="records">充电记录</TabsTrigger>
            <TabsTrigger value="statistics">统计分析</TabsTrigger>
          </TabsList>

          <TabsContent value="records" className="space-y-4">
            {/* 筛选工具栏 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center text-lg">
                  <Filter className="mr-2 h-5 w-5" />
                  筛选条件
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  <div>
                    <Label htmlFor="pile-type">充电模式</Label>
                    <Select 
                      value={filters.pile_type} 
                      onValueChange={(value) => handleFilterChange('pile_type', value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="全部" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">全部</SelectItem>
                        <SelectItem value="fast">快充</SelectItem>
                        <SelectItem value="slow">慢充</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label htmlFor="start-date">开始日期</Label>
                    <Input
                      type="date"
                      value={filters.start_date}
                      onChange={(e) => handleFilterChange('start_date', e.target.value)}
                    />
                  </div>

                  <div>
                    <Label htmlFor="end-date">结束日期</Label>
                    <Input
                      type="date"
                      value={filters.end_date}
                      onChange={(e) => handleFilterChange('end_date', e.target.value)}
                    />
                  </div>

                  <div>
                    <Label htmlFor="order-by">排序</Label>
                    <Select 
                      value={filters.order_by} 
                      onValueChange={(value) => handleFilterChange('order_by', value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="-start_time">时间 (最新)</SelectItem>
                        <SelectItem value="start_time">时间 (最早)</SelectItem>
                        <SelectItem value="-charging_amount">充电量 (高到低)</SelectItem>
                        <SelectItem value="charging_amount">充电量 (低到高)</SelectItem>
                        <SelectItem value="-total_cost">费用 (高到低)</SelectItem>
                        <SelectItem value="total_cost">费用 (低到高)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex justify-between items-center mt-4">
                  <div className="flex space-x-2">
                    <Button onClick={clearFilters} variant="outline" size="sm">
                      清除筛选
                    </Button>
                    <Button onClick={fetchData} variant="outline" size="sm">
                      <RefreshCw className="mr-2 h-4 w-4" />
                      刷新
                    </Button>
                    
                    {/* 页面大小选择器 */}
                    <div className="flex items-center space-x-2">
                      <Label className="text-sm">每页显示:</Label>
                      <Select 
                        value={pagination.pageSize.toString()} 
                        onValueChange={(value) => {
                          setPagination(prev => ({ 
                            ...prev, 
                            pageSize: parseInt(value),
                            page: 1  // 重置到第一页
                          }));
                        }}
                      >
                        <SelectTrigger className="w-20">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="5">5</SelectItem>
                          <SelectItem value="10">10</SelectItem>
                          <SelectItem value="20">20</SelectItem>
                          <SelectItem value="50">50</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <Button onClick={handleExport} disabled={exporting} size="sm">
                    <FileDown className="mr-2 h-4 w-4" />
                    {exporting ? '导出中...' : '导出CSV'}
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* 记录表格 */}
            <Card>
              <CardHeader>
                <CardTitle>充电记录</CardTitle>
                <CardDescription>
                  共 {pagination.totalCount} 条记录
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>充电时间</TableHead>
                      <TableHead>充电桩</TableHead>
                      <TableHead>模式</TableHead>
                      <TableHead>充电量</TableHead>
                      <TableHead>时长</TableHead>
                      <TableHead>费用</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {historyData.length > 0 ? (
                      historyData.map((record) => (
                        <TableRow key={record.id}>
                          <TableCell>
                            <div>
                              <div className="font-medium">
                                {format(new Date(record.start_time), 'yyyy-MM-dd', { locale: zhCN })}
                              </div>
                              <div className="text-sm text-gray-500">
                                {format(new Date(record.start_time), 'HH:mm', { locale: zhCN })}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>{record.pile.pile_id}</TableCell>
                          <TableCell>
                            <Badge variant={record.pile.pile_type === 'fast' ? 'default' : 'secondary'}>
                              {record.pile.pile_type === 'fast' ? '快充' : '慢充'}
                            </Badge>
                          </TableCell>
                          <TableCell>{record.charging_amount.toFixed(1)} kWh</TableCell>
                          <TableCell>{formatDuration(record.charging_duration)}</TableCell>
                          <TableCell className="font-semibold">
                            {formatCurrency(record.total_cost)}
                          </TableCell>
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" className="h-8 w-8 p-0">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuLabel>操作</DropdownMenuLabel>
                                <DropdownMenuItem
                                  onClick={() => {
                                    setSelectedRecord(record);
                                    setShowDetailDialog(true);
                                  }}
                                >
                                  查看详情
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                          暂无充电记录
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>

                {/* 分页 */}
                {pagination.totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4">
                    <div className="text-sm text-gray-700 dark:text-gray-300">
                      显示 {(pagination.page - 1) * pagination.pageSize + 1} 到{' '}
                      {Math.min(pagination.page * pagination.pageSize, pagination.totalCount)} 条，
                      共 {pagination.totalCount} 条记录
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPagination(prev => ({ ...prev, page: 1 }))}
                        disabled={pagination.page <= 1}
                      >
                        首页
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPagination(prev => ({ ...prev, page: prev.page - 1 }))}
                        disabled={pagination.page <= 1}
                      >
                        上一页
                      </Button>
                      
                      {/* 页码显示 */}
                      <div className="flex items-center space-x-1">
                        {Array.from({ length: Math.min(5, pagination.totalPages) }, (_, i) => {
                          let pageNum;
                          if (pagination.totalPages <= 5) {
                            pageNum = i + 1;
                          } else if (pagination.page <= 3) {
                            pageNum = i + 1;
                          } else if (pagination.page >= pagination.totalPages - 2) {
                            pageNum = pagination.totalPages - 4 + i;
                          } else {
                            pageNum = pagination.page - 2 + i;
                          }
                          
                          return (
                            <Button
                              key={pageNum}
                              variant={pagination.page === pageNum ? "default" : "outline"}
                              size="sm"
                              className="w-8 h-8 p-0"
                              onClick={() => setPagination(prev => ({ ...prev, page: pageNum }))}
                            >
                              {pageNum}
                            </Button>
                          );
                        })}
                      </div>
                      
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))}
                        disabled={pagination.page >= pagination.totalPages}
                      >
                        下一页
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPagination(prev => ({ ...prev, page: pagination.totalPages }))}
                        disabled={pagination.page >= pagination.totalPages}
                      >
                        末页
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="statistics" className="space-y-4">
            <StatisticsView 
              statistics={statistics} 
              onRefresh={fetchStatistics}
              loading={loading}
            />
          </TabsContent>
        </Tabs>

        {/* 详情对话框 */}
        <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>充电记录详情</DialogTitle>
            </DialogHeader>
            {selectedRecord && (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-semibold mb-2">基本信息</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">充电桩：</span>
                        <span>{selectedRecord.pile.pile_id}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">充电模式：</span>
                        <Badge variant={selectedRecord.pile.pile_type === 'fast' ? 'default' : 'secondary'}>
                          {selectedRecord.pile.pile_type === 'fast' ? '快充' : '慢充'}
                        </Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">开始时间：</span>
                        <span>{format(new Date(selectedRecord.start_time), 'yyyy-MM-dd HH:mm:ss')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">结束时间：</span>
                        <span>{format(new Date(selectedRecord.end_time), 'yyyy-MM-dd HH:mm:ss')}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="font-semibold mb-2">充电信息</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">充电量：</span>
                        <span>{selectedRecord.charging_amount.toFixed(2)} kWh</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">充电时长：</span>
                        <span>{formatDuration(selectedRecord.charging_duration)}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">费用明细</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">峰时费用：</span>
                        <span>{formatCurrency(selectedRecord.peak_cost)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">平时费用：</span>
                        <span>{formatCurrency(selectedRecord.normal_cost)}</span>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">谷时费用：</span>
                        <span>{formatCurrency(selectedRecord.valley_cost)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">服务费：</span>
                        <span>{formatCurrency(selectedRecord.service_cost)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t">
                    <div className="flex justify-between font-semibold">
                      <span>总费用：</span>
                      <span className="text-lg">{formatCurrency(selectedRecord.total_cost)}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}

// 统计分析组件
function StatisticsView({ statistics, onRefresh, loading }) {
  const [selectedPeriod, setSelectedPeriod] = useState('30');
  
  const handlePeriodChange = (days) => {
    setSelectedPeriod(days);
    onRefresh(parseInt(days));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-300">加载统计数据中...</p>
        </div>
      </div>
    );
  }

  if (!statistics || !statistics.statistics) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <BarChart3 className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">暂无统计数据</h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              您在选择的时间段内没有充电记录
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const stats = statistics.statistics;

  return (
    <div className="space-y-6">
      {/* 时间段选择 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center">
              <BarChart3 className="mr-2 h-5 w-5" />
              统计分析
            </span>
            <Select value={selectedPeriod} onValueChange={handlePeriodChange}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">最近7天</SelectItem>
                <SelectItem value="30">最近30天</SelectItem>
                <SelectItem value="90">最近90天</SelectItem>
                <SelectItem value="180">最近半年</SelectItem>
              </SelectContent>
            </Select>
          </CardTitle>
        </CardHeader>
      </Card>

      {/* 基础统计 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">总充电量</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_amount.toFixed(1)} kWh</div>
            <p className="text-xs text-muted-foreground">
              平均每次：{stats.avg_amount.toFixed(1)} kWh
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">总费用</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">¥{stats.total_cost.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">
              平均每次：¥{stats.avg_cost.toFixed(2)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">总时长</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_duration.toFixed(1)}h</div>
            <p className="text-xs text-muted-foreground">
              平均每次：{stats.avg_duration.toFixed(1)}h
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">充电频率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.avg_sessions_per_week.toFixed(1)}</div>
            <p className="text-xs text-muted-foreground">次/周</p>
          </CardContent>
        </Card>
      </div>

      {/* 模式统计 */}
      <Card>
        <CardHeader>
          <CardTitle>充电模式分析</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {stats.mode_statistics.map((mode) => (
              <div key={mode.mode} className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="font-medium">{mode.mode_name}</span>
                  <span className="text-sm text-gray-600">{mode.percentage}%</span>
                </div>
                <Progress value={mode.percentage} className="h-2" />
                <div className="flex justify-between text-sm text-gray-600">
                  <span>{mode.count}次</span>
                  <span>{mode.total_amount.toFixed(1)} kWh</span>
                  <span>¥{mode.total_cost.toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 费用分析 */}
      <Card>
        <CardHeader>
          <CardTitle>费用构成分析</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span>峰时电费</span>
                <span>¥{stats.cost_analysis.peak_cost.toFixed(2)} ({stats.cost_analysis.peak_percentage}%)</span>
              </div>
              <Progress value={stats.cost_analysis.peak_percentage} className="h-2" />
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span>平时电费</span>
                <span>¥{stats.cost_analysis.normal_cost.toFixed(2)} ({stats.cost_analysis.normal_percentage}%)</span>
              </div>
              <Progress value={stats.cost_analysis.normal_percentage} className="h-2" />
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span>谷时电费</span>
                <span>¥{stats.cost_analysis.valley_cost.toFixed(2)} ({stats.cost_analysis.valley_percentage}%)</span>
              </div>
              <Progress value={stats.cost_analysis.valley_percentage} className="h-2" />
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span>服务费</span>
                <span>¥{stats.cost_analysis.service_cost.toFixed(2)} ({stats.cost_analysis.service_percentage}%)</span>
              </div>
              <Progress value={stats.cost_analysis.service_percentage} className="h-2" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 常用充电桩 */}
      {stats.favorite_piles.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>常用充电桩</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats.favorite_piles.map((pile, index) => (
                <div key={pile.pile_id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded">
                  <div className="flex items-center space-x-3">
                    <Badge variant="outline">#{index + 1}</Badge>
                    <span className="font-medium">{pile.pile_id}</span>
                    <Badge variant={pile.pile_type === '快充' ? 'default' : 'secondary'}>
                      {pile.pile_type}
                    </Badge>
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    使用{pile.usage_count}次 · {pile.total_amount.toFixed(1)}kWh
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
} 