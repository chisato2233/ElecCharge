'use client';

import { DirectionAwareTabs } from '@/components/ui/DirectionAwareTabs';
import { Car, History, LayoutDashboard, Settings } from 'lucide-react';
import DashboardContent from '../dashboard/page';
import HistoryContent from '../history/page';
import VehiclesContent from '../vehicles/page';

export default function DemoPage() {
  const tabs = [
    {
      id: 0,
      label: (
        <div className="flex items-center gap-2">
          <LayoutDashboard size={16} />
          仪表盘
        </div>
      ),
      content: (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
          <DashboardContent />
        </div>
      )
    },
    {
      id: 1,
      label: (
        <div className="flex items-center gap-2">
          <History size={16} />
          充电记录
        </div>
      ),
      content: (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
          <HistoryContent />
        </div>
      )
    },
    {
      id: 2,
      label: (
        <div className="flex items-center gap-2">
          <Car size={16} />
          车辆管理
        </div>
      ),
      content: (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
          <VehiclesContent />
        </div>
      )
    },
    {
      id: 3,
      label: (
        <div className="flex items-center gap-2">
          <Settings size={16} />
          设置
        </div>
      ),
      content: (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
          <div className="text-center">
            <Settings size={64} className="mx-auto mb-4 text-gray-400" />
            <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-2">设置页面</h2>
            <p className="text-gray-600 dark:text-gray-400">系统设置和用户配置</p>
          </div>
        </div>
      )
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-200 mb-2">
            电动车充电站管理系统
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            高级选项卡界面演示 - 支持方向感知动画
          </p>
        </div>
        
        <DirectionAwareTabs
          tabs={tabs}
          className="bg-gray-800 shadow-lg"
          onChange={() => console.log('选项卡切换')}
        />
      </div>
    </div>
  );
} 