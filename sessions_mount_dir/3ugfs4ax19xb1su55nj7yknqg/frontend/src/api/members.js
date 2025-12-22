import axios from 'axios';

const API_BASE_URL = '/api/v1';

/**
 * 获取所有会员列表
 * @returns {Promise<Array>} 会员列表
 */
export const getMembers = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/members`);
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
    const response = await axios.get(`${API_BASE_URL}/members/${id}`);
    return response.data;
  } catch (error) {
    console.error('获取会员详情失败:', error);
    throw error;
  }
};

/**
 * 创建新会员
 * @param {Object} memberData 会员数据
 * @returns {Promise<Object>} 创建的会员数据
 */
export const createMember = async (memberData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/members`, memberData);
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
 * @returns {Promise<Object>} 更新后的会员数据
 */
export const updateMember = async (id, memberData) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/members/${id}`, memberData);
    return response.data;
  } catch (error) {
    console.error('更新会员信息失败:', error);
    throw error;
  }
};

/**
 * 删除会员
 * @param {number} id 会员ID
 * @returns {Promise<void>}
 */
export const deleteMember = async (id) => {
  try {
    await axios.delete(`${API_BASE_URL}/members/${id}`);
  } catch (error) {
    console.error('删除会员失败:', error);
    throw error;
  }
};