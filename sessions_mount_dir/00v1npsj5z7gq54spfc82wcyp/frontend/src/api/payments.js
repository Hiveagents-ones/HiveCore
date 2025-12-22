import axios from 'axios';

const API_BASE_URL = '/api/v1';

/**
 * 获取支付记录列表
 * @param {Object} params - 查询参数
 * @returns {Promise} Axios promise
 */
export const getPayments = (params) => {
  return axios.get(`${API_BASE_URL}/payments`, { params });
};

/**
 * 创建新的支付记录
 * @param {Object} paymentData - 支付数据
 * @returns {Promise} Axios promise
 */
export const createPayment = (paymentData) => {
  return axios.post(`${API_BASE_URL}/payments`, paymentData);
};

/**
 * 获取财务报表
 * @param {Object} params - 查询参数
 * @returns {Promise} Axios promise
 */
export const getFinancialReports = (params) => {
  return axios.get(`${API_BASE_URL}/reports`, { params });
};

/**
 * 获取会员支付记录
 * @param {number} memberId - 会员ID
 * @returns {Promise} Axios promise
 */
export const getMemberPayments = (memberId) => {
  return axios.get(`${API_BASE_URL}/payments`, {
    params: { member_id: memberId }
  });
};

/**
 * 获取课程费用信息
 * @param {number} courseId - 课程ID
 * @returns {Promise} Axios promise
 */
export const getCourseFee = (courseId) => {
  return axios.get(`${API_BASE_URL}/courses/${courseId}/fee`);
};

export default {
  getPayments,
  createPayment,
  getFinancialReports,
  getMemberPayments,
  getCourseFee
};