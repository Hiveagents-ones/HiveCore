import axios from 'axios';

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000';
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1秒

/**
 * 处理API请求错误
 * @param {Error} error 错误对象
 * @throws {Error} 重新抛出错误
 */
function handleApiError(error) {
  if (error.response) {
    // 服务器返回了错误状态码
    console.error('API Error:', error.response.status, error.response.data);
    throw new Error(`请求失败: ${error.response.data.message || error.response.statusText}`);
  } else if (error.request) {
    // 请求已发出但没有收到响应
    console.error('Network Error:', error.message);
    throw new Error('网络错误，请检查您的连接');
  } else {
    // 请求配置出错
    console.error('Request Error:', error.message);
    throw error;
  }
}

/**
 * 带重试机制的请求封装
 * @param {Function} requestFn 请求函数
 * @param {number} retries 剩余重试次数
 * @returns {Promise} Axios promise
 */
async function requestWithRetry(requestFn, retries = MAX_RETRIES) {
  try {
    return await requestFn();
  } catch (error) {
    if (retries <= 0 || !error.response || error.response.status >= 500) {
      handleApiError(error);
    }
    await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
    return requestWithRetry(requestFn, retries - 1);
  }
}

/**
 * 支付结算API客户端
 */
export default {
  /**
   * 获取所有支付记录（带重试机制）
   * @returns {Promise} Axios promise
   */
  getAllPayments() {
    return requestWithRetry(
      () => axios.get(`${API_BASE_URL}/api/v1/payments`)
    );
  },

  /**
   * 创建新的支付记录（带重试机制）
   * @param {Object} paymentData 支付数据
   * @param {number} paymentData.member_id 会员ID
   * @param {number} paymentData.amount 支付金额
   * @param {string} paymentData.payment_method 支付方式
   * @returns {Promise} Axios promise
   */
  createPayment(paymentData) {
    return requestWithRetry(
      () => axios.post(`${API_BASE_URL}/api/v1/payments`, paymentData)
    );
  },

  /**
   * 获取会员的支付记录（带重试机制）
   * @param {number} memberId 会员ID
   * @returns {Promise} Axios promise
   */
  getPaymentsByMember(memberId) {
    return requestWithRetry(
      () => axios.get(`${API_BASE_URL}/api/v1/payments?member_id=${memberId}`)
    );
  },

  /**
   * 获取支付记录详情（带重试机制）
   * @param {number} paymentId 支付记录ID
   * @returns {Promise} Axios promise
   */
  getPaymentDetail(paymentId) {
    return requestWithRetry(
      () => axios.get(`${API_BASE_URL}/api/v1/payments/${paymentId}`)
    );
  }
};