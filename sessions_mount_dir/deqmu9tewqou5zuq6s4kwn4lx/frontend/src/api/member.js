import axios from 'axios';

// 创建axios实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
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

// 会员API接口
export const memberApi = {
  // 获取会员列表
  getMembers(params = {}) {
    return api.get('/members', { params });
  },

  // 获取单个会员详情
  getMember(id) {
    return api.get(`/members/${id}`);
  },

  // 创建会员
  createMember(data) {
    return api.post('/members', data);
  },

  // 更新会员信息
  updateMember(id, data) {
    return api.put(`/members/${id}`, data);
  },

  // 删除会员
  deleteMember(id) {
    return api.delete(`/members/${id}`);
  },

  // 批量删除会员
  batchDeleteMembers(ids) {
    return api.post('/members/batch-delete', { ids });
  },

  // 导出会员数据
  exportMembers(params = {}) {
    return api.get('/members/export', {
      params,
      responseType: 'blob',
    });
  },

  // 导入会员数据
  importMembers(file) {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/members/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // 获取会员统计信息
  getMemberStats() {
    return api.get('/members/stats');
  },

  // 更新会员等级
  updateMemberLevel(id, level) {
    return api.patch(`/members/${id}/level`, { level });
  },

  // 续费会员
  renewMembership(id, expiryDate) {
    return api.post(`/members/${id}/renew`, { expiry_date: expiryDate });
  },

  // 搜索会员
  searchMembers(keyword) {
    return api.get('/members/search', {
      params: { q: keyword },
    });
  },
};

export default memberApi;