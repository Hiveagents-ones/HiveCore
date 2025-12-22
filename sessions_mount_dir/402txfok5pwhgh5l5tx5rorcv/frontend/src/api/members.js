import axios from 'axios';

const API_BASE_URL = '/api/v1/members';

/**
 * 获取会员列表
 * @param {Object} params - 查询参数
 * @returns {Promise} 会员列表数据
 */
export const getMembers = async (params = {}) => {
  try {
    const response = await axios.get(API_BASE_URL, { params });
    return response.data;
  } catch (error) {
    console.error('获取会员列表失败:', error);
    throw error;
  }
};

/**
 * 获取单个会员详情
 * @param {number} id - 会员ID
 * @returns {Promise} 会员详情数据
 */
export const getMember = async (id) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/${id}`);
    return response.data;
  } catch (error) {
    console.error('获取会员详情失败:', error);
    throw error;
  }
};

/**
 * 创建新会员
 * @param {Object} memberData - 会员数据
 * @returns {Promise} 创建的会员数据
 */
export const createMember = async (memberData) => {
  try {
    const response = await axios.post(API_BASE_URL, memberData);
    return response.data;
  } catch (error) {
    console.error('创建会员失败:', error);
    throw error;
  }
};

/**
 * 更新会员信息
 * @param {number} id - 会员ID
 * @param {Object} memberData - 更新的会员数据
 * @returns {Promise} 更新后的会员数据
 */
export const updateMember = async (id, memberData) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/${id}`, memberData);
    return response.data;
  } catch (error) {
    console.error('更新会员失败:', error);
    throw error;
  }
};

/**
 * 删除会员
 * @param {number} id - 会员ID
 * @returns {Promise} 删除结果
 */
export const deleteMember = async (id) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/${id}`);
    return response.data;
  } catch (error) {
    console.error('删除会员失败:', error);
    throw error;
  }
};

/**
 * 获取会员入场记录
 * @param {number} memberId - 会员ID
 * @param {Object} params - 查询参数
 * @returns {Promise} 入场记录数据
 */
export const getMemberEntryRecords = async (memberId, params = {}) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/${memberId}/entry_records`, { params });
    return response.data;
  } catch (error) {
    console.error('获取会员入场记录失败:', error);
    throw error;
  }
};

/**
 * 创建会员入场记录
 * @param {number} memberId - 会员ID
 * @param {Object} recordData - 入场记录数据
 * @returns {Promise} 创建的入场记录数据
 */
export const createMemberEntryRecord = async (memberId, recordData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/${memberId}/entry_records`, recordData);
    return response.data;
  } catch (error) {
    console.error('创建会员入场记录失败:', error);
    throw error;
  }
};

export default {
  getMembers,
  getMember,
  createMember,
  updateMember,
  deleteMember,
  getMemberEntryRecords,
  createMemberEntryRecord
};
