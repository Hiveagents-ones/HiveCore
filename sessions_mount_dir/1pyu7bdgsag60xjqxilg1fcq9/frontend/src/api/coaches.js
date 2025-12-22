import axios from 'axios';
import { getToken } from './auth';

const apiClient = axios.create({
  baseURL: '/api/v1',
  withCredentials: false,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json'
  }
});

// 设置请求拦截器添加认证token
apiClient.interceptors.request.use(config => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default {
  // 获取所有教练
  getCoaches() {
    return apiClient.get('/coaches');
  },
  
  // 获取单个教练详情
  getCoach(id) {
    return apiClient.get(`/coaches/${id}`);
  },
  
  // 创建教练
  createCoach(coachData) {
    return apiClient.post('/coaches', coachData);
  },
  
  // 更新教练信息
  updateCoach(id, coachData) {
    return apiClient.put(`/coaches/${id}`, coachData);
  },
  
  // 删除教练
  deleteCoach(id) {
    return apiClient.delete(`/coaches/${id}`);
  },
  
  // 获取教练排班表
  getCoachSchedule(id) {
    return apiClient.get(`/coaches/${id}/schedule`);
  },
  
  // 更新教练排班表
  updateCoachSchedule(id, scheduleData) {
    return apiClient.put(`/coaches/${id}/schedule`, scheduleData);
  },
  
  // 批量更新教练排班
  batchUpdateSchedules(scheduleUpdates) {
    return apiClient.post('/coaches/schedules/batch', scheduleUpdates);
  }
}