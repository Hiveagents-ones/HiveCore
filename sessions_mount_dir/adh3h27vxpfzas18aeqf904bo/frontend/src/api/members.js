import axios from 'axios';

const API_BASE_URL = '/api/v1';

/**
 * 获取所有会员列表
 * @returns {Promise} 包含会员列表的Promise
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
 * @param {number} memberId 会员ID
 * @returns {Promise} 包含会员详情的Promise
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
 * 创建新会员
 * @param {Object} memberData 会员数据
 * @returns {Promise} 包含新会员信息的Promise
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
 * @param {number} memberId 会员ID
 * @param {Object} memberData 更新的会员数据
 * @returns {Promise} 包含更新结果的Promise
 */
export const updateMember = async (memberId, memberData) => {
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
 * @returns {Promise} 包含删除结果的Promise
 */
export const deleteMember = async (memberId) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/members/${memberId}`);
    return response.data;
  } catch (error) {
    console.error('删除会员失败:', error);
    throw error;
  }
};

/**
 * 获取会员卡状态
 * @param {number} memberId 会员ID
 * @returns {Promise} 包含会员卡状态的Promise
 */
export const getCardStatus = async (memberId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/members/${memberId}/card-status`);
    return response.data;
  } catch (error) {
    console.error('获取会员卡状态失败:', error);
    throw error;
  }
};