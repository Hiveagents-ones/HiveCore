import axios from 'axios';

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || '/api/v1';

/**
 * 支付记录API客户端
 */
const paymentApi = {
  /**
   * 获取所有支付记录
   * @param {Object} params - 查询参数
   * @returns {Promise} Axios promise
   */
  getPayments(params) {
    return axios.get(`${API_BASE_URL}/payments`, { params });
  },

  /**
   * 创建支付记录
   * @param {Object} paymentData - 支付数据
   * @returns {Promise} Axios promise
   */
  createPayment(paymentData) {
    return axios.post(`${API_BASE_URL}/payments`, paymentData);
  },

  /**
   * 获取会员的支付记录
   * @param {number} memberId - 会员ID
   * @param {Object} params - 查询参数
   * @returns {Promise} Axios promise
   */
  getMemberPayments(memberId, params) {
    return axios.get(`${API_BASE_URL}/members/${memberId}/payments`, { params });
  },

  /**
   * 获取支付记录详情
   * @param {number} paymentId - 支付记录ID
   * @returns {Promise} Axios promise
   */
  getPaymentDetails(paymentId) {
    return axios.get(`${API_BASE_URL}/payments/${paymentId}`);
  },

  /**
   * 更新支付记录
   * @param {number} paymentId - 支付记录ID
   * @param {Object} updateData - 更新数据
   * @returns {Promise} Axios promise
   */
  updatePayment(paymentId, updateData) {
    return axios.put(`${API_BASE_URL}/payments/${paymentId}`, updateData);
  },

  /**
   * 删除支付记录
   * @param {number} paymentId - 支付记录ID
   * @returns {Promise} Axios promise
   */
  deletePayment(paymentId) {
    return axios.delete(`${API_BASE_URL}/payments/${paymentId}`);
  }
};

export default paymentApi;