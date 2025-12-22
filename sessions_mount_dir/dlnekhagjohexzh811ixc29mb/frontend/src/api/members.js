import axios from 'axios';

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || '/api/v1';

/**
 * 获取所有会员列表
 * @returns {Promise<Array>} 会员列表
 */
export const getMembers = async () => {
  const response = await axios.get(`${API_BASE_URL}/members`, {
    params: {
      page: 1,
      page_size: 100
    }
  });
  try {
    
    return response.data;
  } catch (error) {
    console.error('获取会员列表失败:', error);
    throw error;
  }
};

/**
 * 创建新会员
 * @param {Object} memberData 会员数据
 * @returns {Promise<Object>} 新创建的会员
 */
export const createMember = async (memberData) => {
  // 会员数据字段验证
  if (!memberData.name || !memberData.email) {
    throw new Error('姓名和邮箱为必填项');
  }
  try {
    const response = await axios.post(`${API_BASE_URL}/members`, memberData);
    return response.data;
  } catch (error) {
    console.error('创建会员失败:', error);
    throw error;
  }
};

/**
 * 获取单个会员详情
 * @param {number} memberId 会员ID
 * @returns {Promise<Object>} 会员详情
 */
export const getMemberById = async (memberId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/members/${memberId}`);
    return response.data;
  } catch (error) {
    console.error('获取会员详情失败:', error);
    throw error;
  }
};

/**
 * 更新会员信息
 * @param {number} memberId 会员ID
 * @param {Object} memberData 更新的会员数据
 * @returns {Promise<Object>} 更新后的会员
 */
export const updateMember = async (memberId, memberData) => {
  // 会员数据字段验证
  if (!memberData.name || !memberData.email) {
    throw new Error('姓名和邮箱为必填项');
  }
  try {
    const response = await axios.put(`${API_BASE_URL}/members/${memberId}`, memberData);
    return response.data;
  } catch (error) {
    console.error('更新会员失败:', error);
    throw error;
  }
};

/**
 * 删除会员
 * @param {number} memberId 会员ID
 * @returns {Promise<void>}
 */
export const deleteMember = async (memberId) => {
  // 添加请求拦截器
  axios.interceptors.request.use(config => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  }, error => {
    return Promise.reject(error);
  });
  try {
    await axios.delete(`${API_BASE_URL}/members/${memberId}`);
  } catch (error) {
    console.error('删除会员失败:', error);
    throw error;
  }
};
