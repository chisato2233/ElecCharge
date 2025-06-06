'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

export function BottomNavigation({ tabs, activeTab, onChange, className }) {
  const handleTabClick = (tabId) => {
    // 触觉反馈（如果设备支持）
    if (navigator.vibrate) {
      navigator.vibrate(50);
    }
    onChange(tabId);
  };

  return (
    <motion.div
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.3, type: "spring", stiffness: 400, damping: 30 }}
      className={cn(
        "fixed bottom-4 left-4 right-4 z-50 md:hidden",
        "bg-white/90 dark:bg-black/90 backdrop-blur-2xl",
        "border border-gray-200/30 dark:border-gray-800/30",
        "rounded-3xl shadow-2xl shadow-black/10 dark:shadow-black/50",
        className
      )}
    >
      <div className="flex items-center justify-around px-1 py-2">
        {tabs.map((tab, index) => (
          <motion.button
            key={tab.id}
            onClick={() => handleTabClick(tab.id)}
            className={cn(
              "relative flex flex-col items-center justify-center",
              "px-3 py-3 rounded-2xl transition-all duration-300",
              "min-w-[60px] min-h-[60px]",
              activeTab === tab.id
                ? "text-blue-600 dark:text-blue-400"
                : "text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
            )}
            whileTap={{ scale: 0.9 }}
            whileHover={{ scale: 1.05 }}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            {/* 活跃状态背景 */}
            {activeTab === tab.id && (
              <motion.div
                layoutId="bottomNavBubble"
                className="absolute inset-0 bg-blue-50 dark:bg-blue-950/50 rounded-2xl border border-blue-200/50 dark:border-blue-800/50"
                transition={{ type: "spring", bounce: 0.15, duration: 0.5 }}
              />
            )}
            
            {/* 图标容器 */}
            <motion.div
              className="relative z-10 mb-1"
              animate={{
                scale: activeTab === tab.id ? 1.15 : 1,
                y: activeTab === tab.id ? -2 : 0,
              }}
              transition={{ duration: 0.3, type: "spring", stiffness: 400 }}
            >
              {tab.icon}
            </motion.div>
            
            {/* 文字标签 */}
            <motion.span
              className="relative z-10 text-xs font-medium leading-tight text-center"
              animate={{
                opacity: activeTab === tab.id ? 1 : 0.7,
                fontWeight: activeTab === tab.id ? 600 : 500,
                scale: activeTab === tab.id ? 1.05 : 1,
              }}
              transition={{ duration: 0.3 }}
            >
              {tab.title}
            </motion.span>
            
            {/* 活跃状态指示器 */}
            {activeTab === tab.id && (
              <motion.div
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                className="absolute -top-1 left-1/2 transform -translate-x-1/2 w-1.5 h-1.5 bg-blue-600 dark:bg-blue-400 rounded-full"
                transition={{ duration: 0.2 }}
              />
            )}
            
            {/* 点击涟漪效果 */}
            <motion.div
              className="absolute inset-0 rounded-2xl"
              whileTap={{
                background: [
                  "rgba(59, 130, 246, 0)",
                  "rgba(59, 130, 246, 0.1)",
                  "rgba(59, 130, 246, 0)"
                ]
              }}
              transition={{ duration: 0.3 }}
            />
          </motion.button>
        ))}
      </div>
      
      {/* 底部安全区域指示器 */}
      <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-8 h-1 bg-gray-300 dark:bg-gray-700 rounded-full opacity-50" />
    </motion.div>
  );
} 