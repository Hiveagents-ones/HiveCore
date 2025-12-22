import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * 获取会员列表
 * @param {Object} params - 查询参数
 * @returns {Promise} Axios promise
 */
export const getMembers = (params = {}) => {
  return axios.get(`${API_BASE_URL}/api/v1/members`, { params });
};

/**
 * 创建新会员
 * @param {Object} memberData - 会员数据
 * @returns {Promise} Axios promise
 */
export const createMember = (memberData) => {
  return axios.post(`${API_BASE_URL}/api/v1/members`, memberData);
};

/**
 * 获取单个会员详情
 * @param {number} memberId - 会员ID
 * @returns {Promise} Axios promise
 */
export const getMemberById = (memberId) => {
  return axios.get(`${API_BASE_URL}/api/v1/members/${memberId}`);
};

/**
 * 更新会员信息
 * @param {number} memberId - 会员ID
 * @param {Object} memberData - 更新的会员数据
 * @returns {Promise} Axios promise
 */
export const updateMember = (memberId, memberData) => {
  return axios.put(`${API_BASE_URL}/api/v1/members/${memberId}`, memberData);
};

/**
 * 删除会员
 * @param {number} memberId - 会员ID
 * @returns {Promise} Axios promise
 */
export const deleteMember = (memberId) => {
  return axios.delete(`${API_BASE_URL}/api/v1/members/${memberId}`);
};

/**
 * 获取会员支付记录
 * @param {number} memberId - 会员ID
 * @returns {Promise} Axios promise
 */
export const getMemberPayments = (memberId) => {
  return axios.get(`${API_BASE_URL}/api/v1/members/${memberId}/payments`);
};

/**
 * 获取会员预约记录
 * @param {number} memberId - 会员ID
 * @returns {Promise} Axios promise
 */
export const getMemberBookings = (memberId) => {
  return axios.get(`${API_BASE_URL}/api/v1/members/${memberId}/bookings`);
};

/**
 * 更新会员卡状态
 * @param {number} memberId - 会员ID
 * @param {string} status - 新的卡状态
 * @returns {Promise} Axios promise
 */
export const updateMemberCardStatus = (memberId, status) => {
  return axios.patch(`${API_BASE_URL}/api/v1/members/${memberId}/card-status`, { status });
};
  return axios.get(`${API_BASE_URL}/api/v1/members/${memberId}/payments`);
};
