'use client';

import { createContext, useContext, useState, useEffect, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { authAPI } from '@/lib/auth';

const AuthContext = createContext();

// 本地缓存键
const USER_CACHE_KEY = 'cached_user_info';
const CACHE_EXPIRY_KEY = 'user_cache_expiry';
const CACHE_DURATION = 5 * 60 * 1000; // 5分钟缓存

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);
  const router = useRouter();
  const pathname = usePathname();
  
  // 使用ref防止重复初始化
  const initRef = useRef(false);

  // 检查缓存是否有效
  const isCacheValid = () => {
    try {
      const cacheExpiry = localStorage.getItem(CACHE_EXPIRY_KEY);
      if (!cacheExpiry) return false;
      return Date.now() < parseInt(cacheExpiry);
    } catch {
      return false;
    }
  };

  // 从缓存获取用户信息
  const getCachedUser = () => {
    try {
      if (!isCacheValid()) return null;
      const cachedUser = localStorage.getItem(USER_CACHE_KEY);
      return cachedUser ? JSON.parse(cachedUser) : null;
    } catch {
      return null;
    }
  };

  // 缓存用户信息
  const cacheUser = (userData) => {
    try {
      localStorage.setItem(USER_CACHE_KEY, JSON.stringify(userData));
      localStorage.setItem(CACHE_EXPIRY_KEY, (Date.now() + CACHE_DURATION).toString());
    } catch (error) {
      console.warn('缓存用户信息失败:', error);
    }
  };

  // 清除缓存
  const clearCache = () => {
    try {
      localStorage.removeItem(USER_CACHE_KEY);
      localStorage.removeItem(CACHE_EXPIRY_KEY);
    } catch (error) {
      console.warn('清除缓存失败:', error);
    }
  };

  // 处理无效token
  const handleInvalidToken = () => {
    localStorage.removeItem('auth_token');
    clearCache();
    setUser(null);
    setInitialized(true); // 确保设置为已初始化
    setLoading(false);    // 确保停止加载
    if (pathname !== '/login') {
      router.push('/login');
    }
  };

  // 初始化认证状态（仅执行一次）
  useEffect(() => {
    // 防止重复初始化
    if (initRef.current) return;
    initRef.current = true;
    
    const initAuth = async () => {
      const token = localStorage.getItem('auth_token');
      
      if (!token) {
        // 没有token的情况
        setUser(null);
        setLoading(false);
        setInitialized(true);
        if (pathname !== '/login') {
          router.push('/login');
        }
        return;
      }

      // 先尝试从缓存获取用户信息
      const cachedUser = getCachedUser();
      if (cachedUser) {
        setUser(cachedUser);
        setLoading(false);
        setInitialized(true);
        
        // 后台验证token有效性（不阻塞UI）
        authAPI.getProfile().then(response => {
          if (response.success) {
            // 更新缓存
            cacheUser(response.data);
            setUser(response.data);
          } else {
            // Token无效，清除状态
            handleInvalidToken();
          }
        }).catch(() => {
          // 网络错误时保持缓存的用户信息
          console.warn('后台验证token失败，保持缓存状态');
        });
        return;
      }

      // 没有缓存，需要验证token
      try {
        const response = await authAPI.getProfile();
        if (response.success) {
          setUser(response.data);
          cacheUser(response.data);
        } else {
          handleInvalidToken();
          return;
        }
      } catch (error) {
        console.error('获取用户信息失败:', error);
        handleInvalidToken();
        return;
      }
      
      // 确保最终状态正确设置
      setLoading(false);
      setInitialized(true);
    };

    initAuth();
  }, []); // 只在组件挂载时执行一次

  // 登录函数
  const login = async (credentials) => {
    try {
      const response = await authAPI.login(credentials);
      if (response.success) {
        localStorage.setItem('auth_token', response.data.token);
        setUser(response.data.user);
        cacheUser(response.data.user);
        setInitialized(true); // 确保初始化状态正确
        router.push('/dashboard');
        return { success: true };
      } else {
        return { success: false, error: response.error };
      }
    } catch (error) {
      console.error('登录失败:', error);
      return { success: false, error: error.response?.data?.error || { message: error.message } };
    }
  };

  // 登出函数
  const logout = async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      console.error('登出失败:', error);
    } finally {
      localStorage.removeItem('auth_token');
      clearCache();
      setUser(null);
      setInitialized(true); // 保持初始化状态
      router.push('/login');
    }
  };

  // 刷新用户信息
  const refreshUser = async () => {
    try {
      const response = await authAPI.getProfile();
      if (response.success) {
        setUser(response.data);
        cacheUser(response.data);
      }
    } catch (error) {
      console.error('刷新用户信息失败:', error);
    }
  };

  // 检查是否已登录
  const isAuthenticated = user !== null;

  const value = {
    user,
    loading,
    initialized,
    isAuthenticated,
    login,
    logout,
    refreshUser
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
} 