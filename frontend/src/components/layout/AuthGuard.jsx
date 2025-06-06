'use client';

import { useAuth } from '@/contexts/AuthContext';
import { usePathname } from 'next/navigation';

const publicRoutes = ['/login'];

export default function AuthGuard({ children }) {
  const { loading, initialized, user } = useAuth();
  const pathname = usePathname();

  const isPublicRoute = publicRoutes.includes(pathname);

  console.log('AuthGuard状态:', { loading, initialized, user: !!user, pathname });

  // 如果是公开路由，直接显示内容
  if (isPublicRoute) {
    console.log('公开路由，直接显示');
    return children;
  }

  // 如果还在初始化中，显示加载界面
  if (loading && !initialized) {
    console.log('显示加载界面');
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-300">正在初始化...</p>
        </div>
      </div>
    );
  }

  // 初始化完成，直接显示内容
  console.log('显示页面内容');
  return children;
} 