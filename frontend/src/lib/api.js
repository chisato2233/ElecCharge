import axios from 'axios';

// 开发环境使用本地API，生产环境使用Railway
const API_BASE_URL = process.env.NODE_ENV === 'development' 
  ? 'http://localhost:8000/api'  // 本地开发
  : (process.env.NEXT_PUBLIC_API_URL || 'https://elecharge-backend.up.railway.app/api'); // 生产环境

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加认证token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Token ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
