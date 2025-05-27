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
  
  cancelRequest: async (requestId) => {
    const response = await api.delete(`/charging/request/${requestId}/cancel/`);
    return response.data;
  },
  
  completeCharging: async () => {
    const response = await api.post('/charging/complete/');
    return response.data;
  },
  
  // 状态查询
  getQueueStatus: async () => {
    const response = await api.get('/charging/queue/status/');
    return response.data;
  },
  
  getPilesStatus: async () => {
    const response = await api.get('/charging/piles/status/');
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
