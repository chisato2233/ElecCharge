import api from './api';

export const chargingAPI = {
  // 充电请求
  submitRequest: async (requestData) => {
    const response = await api.post('/charging/request/', requestData);
    return response.data;
  },
  
  getRequestStatus: async () => {
    const response = await api.get('/charging/request/status/');
    return response.data;
  },
  
  // 获取当前用户的所有活跃充电请求
  getAllActiveRequests: async () => {
    const response = await api.get('/charging/requests/active/');
    return response.data;
  },
  
  // 智能状态检查：只在可能有请求时才调用
  checkRequestStatusSafely: async () => {
    try {
      const response = await api.get('/charging/request/status/');
      return { success: true, data: response.data };
    } catch (error) {
      if (error.response?.status === 404) {
        // 没有活跃请求，这是正常情况
        return { success: false, noRequest: true };
      }
      throw error; // 其他错误继续抛出
    }
  },
  
    cancelRequest: async (requestId) => {
    const response = await api.delete(`/charging/request/${requestId}/cancel/`);
    return response.data;
  },

  changeChargingMode: async (requestId, newMode) => {
    const response = await api.post(`/charging/request/${requestId}/change-mode/`, {
      charging_mode: newMode
    });
    return response.data;
  },

  completeCharging: async (requestId) => {
    const response = await api.post('/charging/complete/', { request_id: requestId });
    return response.data;
  },
  
  // 状态查询
  getQueueStatus: async () => {
    const response = await api.get('/charging/queue/status/');
    return response.data;
  },
  
  // 新的增强队列状态API - 支持多级队列
  getEnhancedQueueStatus: async () => {
    const response = await api.get('/charging/queue/enhanced/');
    return response.data;
  },
  
  getPilesStatus: async () => {
    const response = await api.get('/charging/piles/status/');
    return response.data;
  },
  
  // 公开的系统状态（不需要认证）
  getPublicSystemStatus: async () => {
    const response = await api.get('/charging/status/');
    return response.data;
  },
  
  // 系统参数
  getSystemParameters: async () => {
    const response = await api.get('/charging/system_parameters/');
    return response.data;
  },
  
  // 账单
  getBills: async (params = {}) => {
    const response = await api.get('/charging/bills/', { params });
    return response.data;
  },
  
  getBillDetail: async (billId) => {
    const response = await api.get(`/charging/bills/${billId}/`);
    return response.data;
  },
  
  // 历史记录相关API
  getChargingHistory: async (params = {}) => {
    const response = await api.get('/charging/history/', { params });
    return response.data;
  },
  
  getChargingStatistics: async (days = 30) => {
    const response = await api.get('/charging/history/statistics/', { 
      params: { days } 
    });
    return response.data;
  },
  
  getChargingSummary: async () => {
    const response = await api.get('/charging/history/summary/');
    return response.data;
  },
  
  exportChargingHistory: async (params = {}) => {
    const response = await api.get('/charging/history/export/', { 
      params,
      responseType: 'blob'
    });
    return response;
  },
  
  // 通知
  getNotifications: async () => {
    const response = await api.get('/charging/notifications/');
    return response.data;
  },
  
  markNotificationRead: async (notificationId) => {
    const response = await api.put(`/charging/notifications/${notificationId}/read/`);
    return response.data;
  }
};
