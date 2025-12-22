import axios from 'axios';

const api = axios.create({
  baseURL: process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 会员管理相关API
export const memberAPI = {
  // 获取会员列表
  getMembers: (params = {}) => {
    return api.get('/api/members', { params });
  },

  // 获取会员详情
  getMemberById: (id) => {
    return api.get(`/api/members/${id}`);
  },

  // 获取会员预约记录
  getMemberAppointments: (id, params = {}) => {
    return api.get(`/api/members/${id}/appointments`, { params });
  },

  // 获取会员消费记录
  getMemberConsumption: (id, params = {}) => {
    return api.get(`/api/members/${id}/consumption`, { params });
  },

  // 更新会员标签
  updateMemberTags: (id, tags) => {
    return api.put(`/api/members/${id}/tags`, { tags });
  },

  // 更新会员备注
  updateMemberNote: (id, note) => {
    return api.put(`/api/members/${id}/note`, { note });
  },

  // 创建会员
  createMember: (data) => {
    return api.post('/api/members', data);
  },

  // 更新会员信息
  updateMember: (id, data) => {
    return api.put(`/api/members/${id}`, data);
  },

  // 删除会员
  deleteMember: (id) => {
    return api.delete(`/api/members/${id}`);
  },

  // 搜索会员
  searchMembers: (query) => {
    return api.get('/api/members/search', { params: { q: query } });
  },

  // 获取会员统计信息
  getMemberStats: (params = {}) => {
    return api.get('/api/members/stats', { params });
  },
};

// 导出默认实例
export default api;
