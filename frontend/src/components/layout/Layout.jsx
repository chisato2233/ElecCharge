// import { useState, useEffect } from 'react';
// import Link from 'next/link';
// import { usePathname, useRouter } from 'next/navigation';
// import { Button } from '@/components/ui/button';
// import { Avatar, AvatarFallback } from '@/components/ui/avatar';
// import { 
//   DropdownMenu, 
//   DropdownMenuContent, 
//   DropdownMenuItem, 
//   DropdownMenuTrigger 
// } from '@/components/ui/dropdown-menu';
// import { Bell, User, LogOut, Zap, Car, BarChart3, Home, History } from 'lucide-react';
// import { useAuth } from '@/contexts/AuthContext';

// export default function Layout({ children }) {
//   const { user, isAuthenticated, logout } = useAuth();
//   const [notifications, setNotifications] = useState([]);
//   const pathname = usePathname();

//   // 如果未认证，直接返回children（让AuthProvider处理重定向）
//   if (!isAuthenticated) {
//     return children;
//   }

//   const navigation = [
//     { name: '仪表板', href: '/dashboard', icon: Home, current: pathname === '/dashboard' },
//     { name: '发起充电', href: '/charging', icon: Zap, current: pathname === '/charging' },
//     { name: '车辆管理', href: '/vehicles', icon: Car, current: pathname === '/vehicles' },
//     { name: '充电记录', href: '/history', icon: History, current: pathname === '/history' },
//   ];

//   return (
//     <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
//       {/* 顶部导航栏 */}
//       <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
//         <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
//           <div className="flex justify-between items-center h-16">
//             {/* Logo */}
//             <div className="flex items-center">
//               <Link href="/dashboard" className="flex items-center">
//                 <Zap className="h-8 w-8 text-blue-600 dark:text-blue-400" />
//                 <span className="ml-2 text-xl font-bold text-gray-900 dark:text-white">
//                   电动车充电站
//                 </span>
//               </Link>
//             </div>

//             {/* 导航菜单 */}
//             <nav className="hidden md:flex space-x-8">
//               {navigation.map((item) => {
//                 const IconComponent = item.icon;
//                 return (
//                   <Link
//                     key={item.name}
//                     href={item.href}
//                     className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
//                       item.current
//                         ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300'
//                         : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700'
//                     }`}
//                   >
//                     <IconComponent className="mr-2 h-4 w-4" />
//                     {item.name}
//                   </Link>
//                 );
//               })}
//             </nav>

//             {/* 用户菜单 */}
//             <div className="flex items-center space-x-4">
//               {/* 通知 */}
//               <Button variant="ghost" size="sm">
//                 <Bell className="h-5 w-5" />
//                 {notifications.length > 0 && (
//                   <span className="ml-1 bg-red-500 text-white text-xs rounded-full px-1">
//                     {notifications.length}
//                   </span>
//                 )}
//               </Button>

//               {/* 用户菜单 */}
//               <DropdownMenu>
//                 <DropdownMenuTrigger asChild>
//                   <Button variant="ghost" className="relative h-8 w-8 rounded-full">
//                     <Avatar className="h-8 w-8">
//                       <AvatarFallback>
//                         {user?.username?.charAt(0).toUpperCase() || 'U'}
//                       </AvatarFallback>
//                     </Avatar>
//                   </Button>
//                 </DropdownMenuTrigger>
//                 <DropdownMenuContent className="w-56" align="end">
//                   <DropdownMenuItem>
//                     <User className="mr-2 h-4 w-4" />
//                     <span>{user?.username || '用户'}</span>
//                   </DropdownMenuItem>
//                   <DropdownMenuItem onClick={logout}>
//                     <LogOut className="mr-2 h-4 w-4" />
//                     <span>登出</span>
//                   </DropdownMenuItem>
//                 </DropdownMenuContent>
//               </DropdownMenu>
//             </div>
//           </div>
//         </div>
//       </header>

//       {/* 移动端导航菜单 */}
//       <nav className="md:hidden bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
//         <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
//           <div className="flex space-x-4 py-2">
//             {navigation.map((item) => {
//               const IconComponent = item.icon;
//               return (
//                 <Link
//                   key={item.name}
//                   href={item.href}
//                   className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
//                     item.current
//                       ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300'
//                       : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700'
//                   }`}
//                 >
//                   <IconComponent className="mr-2 h-4 w-4" />
//                   {item.name}
//                 </Link>
//               );
//             })}
//           </div>
//         </div>
//       </nav>

//       {/* 主要内容 */}
//       <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
//         {children}
//       </main>
//     </div>
//   );
// }
