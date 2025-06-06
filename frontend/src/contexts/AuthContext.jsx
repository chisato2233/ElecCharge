'use client';

import { createContext, useContext, useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { authAPI } from '@/lib/auth';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  // 初始化认证状态
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('auth_token');
      
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const response = await authAPI.getProfile();
        if (response.success) {
          setUser(response.data);
        } else {
          localStorage.removeItem('auth_token');
        }
      } catch (error) {
        console.error('认证失败:', error);
        localStorage.removeItem('auth_token');
      }
      
      setLoading(false);
    };

    initAuth();
  }, []);

  // 登录函数
  const login = async (credentials) => {
    try {
      const response = await authAPI.login(credentials);
      if (response.success) {
        localStorage.setItem('auth_token', response.data.token);
        setUser(response.data.user);
        router.push('/');
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
      setUser(null);
      router.push('/login');
    }
  };

  // 刷新用户信息
  const refreshUser = async () => {
    try {
      const response = await authAPI.getProfile();
      if (response.success) {
        setUser(response.data);
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