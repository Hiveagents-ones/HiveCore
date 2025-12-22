import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * 获取所有会员列表
 * @returns {Promise<Array>} 会员列表
 */
export const getMembers = async (params = {}) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/v1/members`, { params });
    return response.data;
  } catch (error) {
    console.error('获取会员列表失败:', error);
    throw error;
  }
};

/**
 * 获取单个会员详情
 * @param {number} id 会员ID
 * @returns {Promise<Object>} 会员详情
 */
export const getMemberById = async (id) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/v1/members/${id}`);
    return response.data;
  } catch (error) {
    console.error('获取会员详情失败:', error);
    throw error;
  }
};

/**
 * 创建新会员
 * @param {Object} memberData 会员数据
 * @returns {Promise<Object>} 新创建的会员
 */
export const createMember = async (memberData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/v1/members`, memberData);
    return response.data;
  } catch (error) {
    console.error('创建会员失败:', error);
    throw error;
  }
};

/**
 * 更新会员信息
 * @param {number} id 会员ID
 * @param {Object} memberData 更新的会员数据
 * @returns {Promise<Object>} 更新后的会员
 */
export const updateMember = async (id, memberData) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/api/v1/members/${id}`, memberData);
    return response.data;
  } catch (error) {
    console.error('更新会员失败:', error);
    throw error;
  }
};

/**
 * 删除会员
 * @param {number} id 会员ID
 * @returns {Promise<Object>} 删除结果
 */
export const deleteMember = async (id) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/api/v1/members/${id}`);
    return response.data;
  } catch (error) {
    console.error('删除会员失败:', error);
    throw error;
  }
};

export default {
  getMembers,
  getMemberById,
  createMember,
  updateMember,
  deleteMember
}