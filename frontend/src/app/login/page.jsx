'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Zap, User, UserPlus } from 'lucide-react';
import { ThemeToggle } from '@/components/theme-toggle';
import { authAPI } from '@/lib/auth';

export default function AuthPage() {
  // 登录表单状态
  const [loginData, setLoginData] = useState({
    username: '',
    password: ''
  });

  // 注册表单状态
  const [registerData, setRegisterData] = useState({
    username: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: ''
  });

  const [loginLoading, setLoginLoading] = useState(false);
  const [registerLoading, setRegisterLoading] = useState(false);
  const [loginError, setLoginError] = useState('');
  const [registerError, setRegisterError] = useState('');
  const [registerSuccess, setRegisterSuccess] = useState('');
  
  const router = useRouter();

  // 处理登录
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError('');

    try {
      const response = await authAPI.login(loginData);
      if (response.success) {
        localStorage.setItem('auth_token', response.data.token);
        router.push('/dashboard');
      }
    } catch (error) {
      setLoginError(error.response?.data?.error?.message || '登录失败');
    } finally {
      setLoginLoading(false);
    }
  };

  // 处理注册
  const handleRegister = async (e) => {
    e.preventDefault();
    setRegisterLoading(true);
    setRegisterError('');
    setRegisterSuccess('');

    // 验证密码确认
    if (registerData.password !== registerData.confirmPassword) {
      setRegisterError('两次输入的密码不一致');
      setRegisterLoading(false);
      return;
    }

    try {
      const response = await authAPI.register(registerData);
      
      if (response.success) {
        setRegisterSuccess('注册成功！请使用新账号登录');
        // 清空注册表单
        setRegisterData({
          username: '',
          email: '',
          phone: '',
          password: '',
          confirmPassword: ''
        });
        // 3秒后自动切换到登录tab
        setTimeout(() => {
          document.querySelector('[data-value="login"]')?.click();
        }, 2000);
      }
    } catch (error) {
      setRegisterError(error.response?.data?.error?.message || '注册失败');
    } finally {
      setRegisterLoading(false);
    }
  };

  // 处理登录表单变化
  const handleLoginChange = (e) => {
    setLoginData({
      ...loginData,
      [e.target.name]: e.target.value
    });
  };

  // 处理注册表单变化
  const handleRegisterChange = (e) => {
    setRegisterData({
      ...registerData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background py-12 px-4 sm:px-6 lg:px-8">
      {/* 主题切换按钮 */}
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>

      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <Zap className="mx-auto h-12 w-12 text-primary" />
          <h2 className="mt-6 text-3xl font-extrabold text-foreground">
            电动车充电站系统
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            登录或注册您的账号
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>账号管理</CardTitle>
            <CardDescription>
              选择登录或注册新账号
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="login" data-value="login">
                  <User className="w-4 h-4 mr-2" />
                  登录
                </TabsTrigger>
                <TabsTrigger value="register">
                  <UserPlus className="w-4 h-4 mr-2" />
                  注册
                </TabsTrigger>
              </TabsList>

              {/* 登录Tab */}
              <TabsContent value="login" className="space-y-4 mt-6">
                <form onSubmit={handleLogin} className="space-y-4">
                  {loginError && (
                    <Alert variant="destructive">
                      <AlertDescription>{loginError}</AlertDescription>
                    </Alert>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="login-username">用户名</Label>
                    <Input
                      id="login-username"
                      name="username"
                      type="text"
                      required
                      value={loginData.username}
                      onChange={handleLoginChange}
                      placeholder="请输入用户名"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="login-password">密码</Label>
                    <Input
                      id="login-password"
                      name="password"
                      type="password"
                      required
                      value={loginData.password}
                      onChange={handleLoginChange}
                      placeholder="请输入密码"
                    />
                  </div>

                  <Button 
                    type="submit" 
                    className="w-full" 
                    disabled={loginLoading}
                  >
                    {loginLoading ? '登录中...' : '登录'}
                  </Button>
                </form>
              </TabsContent>

              {/* 注册Tab */}
              <TabsContent value="register" className="space-y-4 mt-6">
                <form onSubmit={handleRegister} className="space-y-4">
                  {registerError && (
                    <Alert variant="destructive">
                      <AlertDescription>{registerError}</AlertDescription>
                    </Alert>
                  )}

                  {registerSuccess && (
                    <Alert>
                      <AlertDescription className="text-green-600">
                        {registerSuccess}
                      </AlertDescription>
                    </Alert>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="register-username">用户名</Label>
                    <Input
                      id="register-username"
                      name="username"
                      type="text"
                      required
                      value={registerData.username}
                      onChange={handleRegisterChange}
                      placeholder="请输入用户名"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="register-email">邮箱</Label>
                    <Input
                      id="register-email"
                      name="email"
                      type="email"
                      required
                      value={registerData.email}
                      onChange={handleRegisterChange}
                      placeholder="请输入邮箱地址"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="register-phone">手机号</Label>
                    <Input
                      id="register-phone"
                      name="phone"
                      type="tel"
                      required
                      value={registerData.phone}
                      onChange={handleRegisterChange}
                      placeholder="请输入手机号"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="register-password">密码</Label>
                    <Input
                      id="register-password"
                      name="password"
                      type="password"
                      required
                      value={registerData.password}
                      onChange={handleRegisterChange}
                      placeholder="请输入密码"
                      minLength={6}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="register-confirm-password">确认密码</Label>
                    <Input
                      id="register-confirm-password"
                      name="confirmPassword"
                      type="password"
                      required
                      value={registerData.confirmPassword}
                      onChange={handleRegisterChange}
                      placeholder="请再次输入密码"
                      minLength={6}
                    />
                  </div>

                  <Button 
                    type="submit" 
                    className="w-full" 
                    disabled={registerLoading}
                  >
                    {registerLoading ? '注册中...' : '注册账号'}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* 测试账号提示 - 适配深色模式 */}
        <Card className="bg-primary/10 border-primary/20">
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-primary font-medium mb-2">
                🧪 测试账号
              </p>
              <p className="text-xs text-muted-foreground">
                用户名: testuser | 密码: test123
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                管理员: admin | 密码: admin123
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
