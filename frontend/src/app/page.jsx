'use client';

import { useAuth } from '@/contexts/AuthContext';
import { DirectionAwareTabs } from '@/components/ui/DirectionAwareTabs';
import { BottomNavigation } from '@/components/ui/BottomNavigation';
import { Car, History, LayoutDashboard, Zap, LogOut, User, Sun, Moon } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useState } from 'react';

// 导入页面组件
import DashboardContent from './dashboard/page';
import HistoryContent from './history/page';
import VehiclesContent from './vehicles/page';
import ChargingContent from './charging/page';

export default function MainApp() {
  const { user, loading, logout, isAuthenticated } = useAuth();
  const { theme, setTheme } = useTheme();
  const router = useRouter();
  
  // 添加选项卡状态管理
  const [activeTab, setActiveTab] = useState(0);

  // 如果正在加载，显示加载界面
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white dark:bg-black">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-300">加载中...</p>
        </div>
      </div>
    );
  }

  // 如果未认证，跳转到登录页
  if (!isAuthenticated) {
    router.push('/login');
    return null;
  }

  const tabs = [
    {
      id: 0,
      label: (
        <div className="flex items-center gap-1 sm:gap-2" title="仪表盘">
          <LayoutDashboard size={16} />
          <span className="hidden sm:inline">仪表盘</span>
        </div>
      ),
      mobileTitle: "仪表盘",
      content: (
        <div className="min-h-screen bg-white dark:bg-black">
          <DashboardContent />
        </div>
      )
    },
    {
      id: 1,
      label: (
        <div className="flex items-center gap-1 sm:gap-2" title="发起充电">
          <Zap size={16} />
          <span className="hidden sm:inline">发起充电</span>
        </div>
      ),
      mobileTitle: "发起充电",
      content: (
        <div className="min-h-screen bg-white dark:bg-black">
          <ChargingContent />
        </div>
      )
    },
    {
      id: 2,
      label: (
        <div className="flex items-center gap-1 sm:gap-2" title="充电记录">
          <History size={16} />
          <span className="hidden sm:inline">充电记录</span>
        </div>
      ),
      mobileTitle: "充电记录",
      content: (
        <div className="min-h-screen bg-white dark:bg-black">
          <HistoryContent />
        </div>
      )
    },
    {
      id: 3,
      label: (
        <div className="flex items-center gap-1 sm:gap-2" title="车辆管理">
          <Car size={16} />
          <span className="hidden sm:inline">车辆管理</span>
        </div>
      ),
      mobileTitle: "车辆管理",
      content: (
        <div className="min-h-screen bg-white dark:bg-black">
          <VehiclesContent />
        </div>
      )
    }
  ];

  return (
    <div className="min-h-screen bg-white dark:bg-black">
      {/* 顶部导航栏 */}
      <header className="bg-white dark:bg-black shadow-sm border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* 左侧品牌区域 */}
            <div className="flex items-center min-w-0">
              <div className="flex-shrink-0">
                <div className="flex items-center space-x-2">
                  <div className="relative">
                    <Zap className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                    <div className="absolute inset-0 bg-blue-600 dark:bg-blue-400 opacity-20 blur-sm rounded-full"></div>
                  </div>
                  <div className="flex flex-col">
                    <h1 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
                      Elecharge
                    </h1>
                    {/* 移动端当前页面指示器 */}
                    <span className="md:hidden text-xs text-gray-500 dark:text-gray-400 font-medium">
                      {tabs.find(tab => tab.id === activeTab)?.mobileTitle || ''}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            
            {/* 中间选项卡区域 - 仅在桌面端显示 */}
            <div className="hidden md:flex flex-1 justify-center px-1 sm:px-4 max-w-md sm:max-w-lg">
              <DirectionAwareTabs
                tabs={tabs.map(tab => ({ 
                  id: tab.id, 
                  label: tab.label 
                }))}
                className="shadow-sm scale-90 sm:scale-100"
                onChange={(newTabId) => {
                  setActiveTab(newTabId);
                  console.log('选项卡切换:', newTabId);
                }}
              />
            </div>
            
            {/* 右侧用户控件区域 */}
            <div className="flex items-center space-x-2 sm:space-x-4 min-w-0">
              <span className="text-sm text-gray-700 dark:text-gray-300 hidden lg:block">
                欢迎，{user?.username || '用户'}
              </span>
              
              {/* 主题切换按钮 */}
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 rounded-full transition-all duration-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                title={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
              >
                <div className="relative">
                  {theme === 'dark' ? (
                    <Sun className="h-4 w-4 rotate-0 scale-100 transition-all duration-200" />
                  ) : (
                    <Moon className="h-4 w-4 rotate-0 scale-100 transition-all duration-200" />
                  )}
                </div>
              </Button>
              
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-8 w-8 rounded-full">
                    <User className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={logout}>
                    <LogOut className="mr-2 h-4 w-4" />
                    退出登录
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>
      </header>

      {/* 主内容区域 */}
      <main className="flex-1">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 2xl:px-16">
          {/* 显示当前激活的选项卡内容 */}
          <div className="min-h-screen pb-20 md:pb-0">
            {tabs.find(tab => tab.id === activeTab)?.content}
          </div>
        </div>
      </main>

      {/* 底部悬浮导航栏 - 仅在移动端显示 */}
      <BottomNavigation
        tabs={[
          {
            id: 0,
            icon: <LayoutDashboard size={20} />,
            title: "仪表盘"
          },
          {
            id: 1,
            icon: <Zap size={20} />,
            title: "发起充电"
          },
          {
            id: 2,
            icon: <History size={20} />,
            title: "充电记录"
          },
          {
            id: 3,
            icon: <Car size={20} />,
            title: "车辆管理"
          }
        ]}
        activeTab={activeTab}
        onChange={setActiveTab}
      />
    </div>
  );
}
