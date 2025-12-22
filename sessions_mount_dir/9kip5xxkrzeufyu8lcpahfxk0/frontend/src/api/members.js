import axios from 'axios';

const API_BASE_URL = '/api/v1';

/**
 * 获取会员列表
 * @param {Object} params - 查询参数
 * @returns {Promise} Axios Promise
 */
const getMembers = (params = {}) => {
  return axios.get(`${API_BASE_URL}/members`, { params });
};

/**
 * 创建新会员
 * @param {Object} memberData - 会员数据
 * @returns {Promise} Axios Promise
 */
const createMember = (memberData) => {
  return axios.post(`${API_BASE_URL}/members`, memberData);
};

/**
 * 获取单个会员详情
 * @param {number} memberId - 会员ID
 * @returns {Promise} Axios Promise
 */
const getMemberById = (memberId) => {
  return axios.get(`${API_BASE_URL}/members/${memberId}`);
};

/**
 * 更新会员信息
 * @param {number} memberId - 会员ID
 * @param {Object} updateData - 更新数据
 * @returns {Promise} Axios Promise
 */
const updateMember = (memberId, updateData) => {
  return axios.put(`${API_BASE_URL}/members/${memberId}`, updateData);
};

/**
 * 删除会员
 * @param {number} memberId - 会员ID
 * @returns {Promise} Axios Promise
 */
const deleteMember = (memberId) => {
  return axios.delete(`${API_BASE_URL}/members/${memberId}`);
};

/**
 * 获取会员卡列表
 * @param {number} memberId - 会员ID
 * @returns {Promise} Axios Promise
 */
const getMemberCards = (memberId) => {
  return axios.get(`${API_BASE_URL}/members/${memberId}/cards`);
};

/**
 * 创建会员卡
 * @param {number} memberId - 会员ID
 * @param {Object} cardData - 卡数据
 * @returns {Promise} Axios Promise
 */
const createMemberCard = (memberId, cardData) => {
  return axios.post(`${API_BASE_URL}/members/${memberId}/cards`, cardData);
};

/**
 * 更新会员卡
 * @param {number} memberId - 会员ID
 * @param {number} cardId - 卡ID
 * @param {Object} updateData - 更新数据
 * @returns {Promise} Axios Promise
 */
const updateMemberCard = (memberId, cardId, updateData) => {


/**
 * 获取会员支付记录
 * @param {number} memberId - 会员ID
 * @returns {Promise} Axios Promise
 */
const getMemberPayments = (memberId) => {
  return axios.get(`${API_BASE_URL}/members/${memberId}/payments`);
};

/**
 * 创建会员支付记录
 * @param {number} memberId - 会员ID
 * @param {Object} paymentData - 支付数据
 * @returns {Promise} Axios Promise
 */
const createMemberPayment = (memberId, paymentData) => {

/**
 * 获取会员预约记录
 * @param {number} memberId - 会员ID
 * @returns {Promise} Axios Promise
 */
const getMemberBookings = (memberId) => {
  return axios.get(`${API_BASE_URL}/members/${memberId}/bookings`);
};

/**
 * 创建会员课程预约
 * @param {number} memberId - 会员ID
 * @param {Object} bookingData - 预约数据
 * @returns {Promise} Axios Promise
 */
const createMemberBooking = (memberId, bookingData) => {
  return axios.post(`${API_BASE_URL}/members/${memberId}/bookings`, bookingData);
};

/**
 * 取消会员课程预约
 * @param {number} memberId - 会员ID
 * @param {number} bookingId - 预约ID
 * @returns {Promise} Axios Promise
 */
const cancelMemberBooking = (memberId, bookingId) => {
  return axios.delete(`${API_BASE_URL}/members/${memberId}/bookings/${bookingId}`);
};
  return axios.post(`${API_BASE_URL}/members/${memberId}/payments`, paymentData);
};
  return axios.post(`${API_BASE_URL}/members/${memberId}/payments`, paymentData);
};
  return axios.put(`${API_BASE_URL}/members/${memberId}/cards/${cardId}`, updateData);
};

export default {
  getMembers,
  createMember,
  getMemberById,
  updateMember,
  deleteMember,
  getMemberCards,
  createMemberCard,
  updateMemberCard,
  getMemberPayments,
  createMemberPayment,
  getMemberBookings,
  createMemberBooking,
  cancelMemberBooking
};