import axios from 'axios';

const API_BASE_URL = '/api/v1';

/**
 * 获取会员卡列表
 * @param {number} memberId - 会员ID
 * @returns {Promise} Axios Promise
 */
export const getMemberCards = (memberId) => {
  return axios.get(`${API_BASE_URL}/members/${memberId}/cards`);
};

/**
 * 创建会员卡
 * @param {number} memberId - 会员ID
 * @param {Object} cardData - 会员卡数据
 * @param {string} cardData.card_number - 卡号
 * @param {string} cardData.expiry_date - 过期日期
 * @param {string} cardData.status - 状态
 * @returns {Promise} Axios Promise
 */
export const createMemberCard = (memberId, cardData) => {
  return axios.post(`${API_BASE_URL}/members/${memberId}/cards`, cardData);
};

/**
 * 更新会员卡信息
 * @param {number} memberId - 会员ID
 * @param {number} cardId - 会员卡ID
 * @param {Object} cardData - 更新的会员卡数据
 * @returns {Promise} Axios Promise
 */
export const updateMemberCard = (memberId, cardId, cardData) => {
  return axios.put(`${API_BASE_URL}/members/${memberId}/cards/${cardId}`, cardData);
};

/**
 * 更新会员卡状态
 * @param {number} memberId - 会员ID
 * @param {number} cardId - 会员卡ID
 * @param {string} status - 新状态
 * @returns {Promise} Axios Promise
 */
export const updateCardStatus = (memberId, cardId, status) => {
  return axios.patch(`${API_BASE_URL}/members/${memberId}/cards/${cardId}/status`, { status });
};

/**
 * 获取所有会员卡（管理员用）
 * @returns {Promise} Axios Promise
 */
export const getAllMemberCards = () => {
  return axios.get(`${API_BASE_URL}/members/cards`);
};

export default {
  getMemberCards,
  createMemberCard,
  updateMemberCard,
  updateCardStatus,
  getAllMemberCards
};