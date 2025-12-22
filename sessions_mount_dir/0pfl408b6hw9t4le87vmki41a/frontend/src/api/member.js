import axios from 'axios';

// 创建 axios 实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加认证 token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理错误
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Token 过期或无效，清除本地存储并跳转到登录页
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 会员 API 接口
export const memberApi = {
  // 获取会员列表
  getMembers: async (params = {}) => {
    const { skip = 0, limit = 100, ...filters } = params;
    return api.get('/members', {
      params: { skip, limit, ...filters },
    });
  },

  // 获取单个会员详情
  getMember: async (id) => {
    return api.get(`/members/${id}`);
  },

  // 创建会员
  createMember: async (memberData) => {
    return api.post('/members', memberData);
  },

  // 更新会员信息
  updateMember: async (id, memberData) => {
    return api.put(`/members/${id}`, memberData);
  },

  // 删除会员
  deleteMember: async (id) => {
    return api.delete(`/members/${id}`);
  },

  // 搜索会员
  searchMembers: async (query) => {
    return api.get('/members/search', {
      params: { q: query },
    });
  },

  // 获取会员统计信息
  getMemberStats: async () => {
    return api.get('/members/stats');
  },

  // 批量导入会员
  importMembers: async (formData) => {
    return api.post('/members/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // 导出会员数据
  exportMembers: async (params = {}) => {
    return api.get('/members/export', {
      params,
      responseType: 'blob',
    });
  },
};

export default memberApi;