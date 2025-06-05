import api from './api';

export const vehicleAPI = {
  // 获取用户车辆列表
  getVehicles: async () => {
    const response = await api.get('/auth/vehicles/');
    return response.data;
  },

  // 添加新车辆
  createVehicle: async (vehicleData) => {
    const response = await api.post('/auth/vehicles/', vehicleData);
    return response.data;
  },

  // 获取特定车辆信息
  getVehicle: async (vehicleId) => {
    const response = await api.get(`/auth/vehicles/${vehicleId}/`);
    return response.data;
  },

  // 更新车辆信息
  updateVehicle: async (vehicleId, vehicleData) => {
    const response = await api.put(`/auth/vehicles/${vehicleId}/`, vehicleData);
    return response.data;
  },

  // 删除车辆
  deleteVehicle: async (vehicleId) => {
    const response = await api.delete(`/auth/vehicles/${vehicleId}/`);
    return response.data;
  },

  // 设置默认车辆
  setDefaultVehicle: async (vehicleId) => {
    const response = await api.post(`/auth/vehicles/${vehicleId}/set-default/`);
    return response.data;
  }
}; 