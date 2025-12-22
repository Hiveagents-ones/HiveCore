import axios from 'axios';
import { getToken } from '../utils/auth';
import { handleResponse, handleError } from '../utils/response';
import { formatDate } from '../utils/date';
import { retryRequest } from '../utils/retry';

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || '/api/v1';

/**
 * 支付相关API
 */
export default {
  /**
   * 创建支付订单
   * @param {Object} paymentData - 支付数据
   * @param {number} paymentData.member_id - 会员ID
   * @param {number} paymentData.amount - 支付金额
   * @param {string} paymentData.payment_method - 支付方式
   * @returns {Promise} axios Promise
   */
  createPayment(paymentData) {
    return retryRequest(
      () => axios.post(`${API_BASE_URL}/payments`, paymentData, {
        headers: {
          'Authorization': `Bearer ${getToken()}`,
          'Content-Type': 'application/json'
        }
      }),
      3, // 最大重试次数
      1000 // 重试间隔(ms)
    )
    .then(handleResponse)
    .catch(handleError);
  },

  /**
   * 获取支付记录
   * @param {Object} params - 查询参数
   * @param {number} [params.member_id] - 会员ID（可选）
   * @param {string} [params.start_date] - 开始日期（可选）
   * @param {string} [params.end_date] - 结束日期（可选）
   * @returns {Promise} axios Promise
   */
  getPayments(params = {}) {
    return retryRequest(
      () => axios.get(`${API_BASE_URL}/payments`, {
        params,
        headers: {
          'Authorization': `Bearer ${getToken()}`
        }
      }),
      3,
      1000
    )
    .then(handleResponse)
    .catch(handleError);
  },

  /**
   * 获取单个支付记录详情
   * @param {number} paymentId - 支付记录ID
   * @returns {Promise} axios Promise
   */
  getPaymentDetail(paymentId) {
    return retryRequest(
      () => axios.get(`${API_BASE_URL}/payments/${paymentId}`, {
        headers: {
          'Authorization': `Bearer ${getToken()}`
        }
      }),
      3,
      1000
    )
    .then(handleResponse)
    .catch(handleError);
  },

  /**
   * 生成发票
   * @param {number} paymentId - 支付记录ID
   * @returns {Promise} axios Promise
   */
  generateInvoice(paymentId) {
    return retryRequest(
      () => axios.post(`${API_BASE_URL}/payments/${paymentId}/invoice`, {}, {
        headers: {
          'Authorization': `Bearer ${getToken()}`,
          'Content-Type': 'application/json'
        }
      }),
      3,
      1000
    )
    .then(handleResponse)
    .catch(handleError);
  },

  /**
   * 获取发票
   * @param {number} paymentId - 支付记录ID
   * @returns {Promise} axios Promise
   */
  getInvoice(paymentId) {
    return retryRequest(
      () => axios.get(`${API_BASE_URL}/payments/${paymentId}/invoice`, {
        headers: {
          'Authorization': `Bearer ${getToken()}`,
          'Accept': 'application/pdf'
        },
        responseType: 'blob'
      }),
      3,
      1000
    )
    .then(handleResponse)
    .catch(handleError);
  },
    .catch(handleError);
    .then(handleResponse)
    })
      }
        'Authorization': `Bearer ${getToken()}`
      headers: {
      params: { period },
  /**
   * 获取支付统计数据
   * @param {string} period - 统计周期 (day/week/month/year)
   * @returns {Promise} axios Promise
   */
  getPaymentStats(period = 'month') {
    return retryRequest(
      () => axios.get(`${API_BASE_URL}/payments/stats`, {
        params: { period },
        headers: {
          'Authorization': `Bearer ${getToken()}`
        }
      }),
      3,
      1000
    )
    .then(handleResponse)
    .catch(handleError);
  }
};