import axios from 'axios';

// 创建axios实例，配置基础URL和超时时间
const api = axios.create({
  baseURL: 'https://api.gym.local', // 确保使用HTTPS
  timeout: 10000, // 10秒超时
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：添加认证token等
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

// 响应拦截器：统一处理错误和响应格式
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    // 处理网络错误
    if (!error.response) {
      console.error('Network Error:', error.message);
      throw new Error('网络连接失败，请检查网络设置');
    }
    
    // 处理HTTP错误状态码
    const { status, data } = error.response;
    let errorMessage = '请求失败';
    
    switch (status) {
      case 400:
        errorMessage = data.message || '请求参数错误';
        break;
      case 401:
        errorMessage = '未授权，请重新登录';
        localStorage.removeItem('token');
        window.location.href = '/login';
        break;
      case 403:
        errorMessage = '拒绝访问';
        break;
      case 404:
        errorMessage = '请求的资源不存在';
        break;
      case 500:
        errorMessage = '服务器内部错误';
        break;
      default:
        errorMessage = data.message || `请求失败 (${status})`;
    }
    
    console.error('API Error:', errorMessage);
    throw new Error(errorMessage);
  }
);

// 会员注册API
export const registerMember = async (memberData) => {
  try {
    const response = await api.post('/members/register', memberData);
    return response;
  } catch (error) {
    console.error('Register member failed:', error);
    throw error;
  }
};

// 获取会员卡类型列表
export const getMembershipTypes = async () => {
  try {
    const response = await api.get('/membership-types');
    return response;
  } catch (error) {
    console.error('Get membership types failed:', error);
    throw error;
  }
};

// 获取会员信息
export const getMemberInfo = async (memberId) => {
  try {
    const response = await api.get(`/members/${memberId}`);
    return response;
  } catch (error) {
    console.error('Get member info failed:', error);
    throw error;
  }
};

// 更新会员信息
export const updateMemberInfo = async (memberId, memberData) => {
  try {
    const response = await api.put(`/members/${memberId}`, memberData);
    return response;
  } catch (error) {
    console.error('Update member info failed:', error);
    throw error;
  }
};

// 删除会员
export const deleteMember = async (memberId) => {
  try {
    const response = await api.delete(`/members/${memberId}`);
    return response;
  } catch (error) {
    console.error('Delete member failed:', error);
    throw error;
  }
};

// 获取会员列表
export const getMembersList = async (params = {}) => {
  try {
    const response = await api.get('/members', { params });
    return response;
  } catch (error) {
    console.error('Get members list failed:', error);
    throw error;
  }
};

export default api;