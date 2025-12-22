import axios from 'axios';
import { getToken } from '@/utils/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/**
 * 创建支付记录
 * @param {Object} paymentData - 支付数据
 * @returns {Promise} axios promise
 */
export const createPayment = (paymentData) => {
  return axios.post(`${API_BASE_URL}/payments`, paymentData, {
    headers: {
      'Authorization': `Bearer ${getToken()}`,
      'Content-Type': 'application/json'
    }
  });
};

/**
 * 获取支付记录列表
 * @param {Object} params - 查询参数
 * @returns {Promise} axios promise
 */
export const getPayments = (params = {}) => {
  return axios.get(`${API_BASE_URL}/payments`, {
    params,
    headers: {
      'Authorization': `Bearer ${getToken()}`
    }
  });
};

/**
 * 请求退款
 * @param {String} paymentId - 支付ID
 * @param {Object} refundData - 退款数据
 * @returns {Promise} axios promise
 */
export const requestRefund = (paymentId, refundData) => {
  return axios.post(`${API_BASE_URL}/payments/${paymentId}/refunds`, refundData, {
    headers: {
      'Authorization': `Bearer ${getToken()}`,
      'Content-Type': 'application/json'
    }
  });
};

/**
 * 生成发票
 * @param {Object} invoiceData - 发票数据
 * @returns {Promise} axios promise
 */
export const generateInvoice = (invoiceData) => {
  return axios.post(`${API_BASE_URL}/invoices`, invoiceData, {
    headers: {
      'Authorization': `Bearer ${getToken()}`,
      'Content-Type': 'application/json'
    }
  });
};

/**
 * 获取发票列表
 * @param {Object} params - 查询参数
 * @returns {Promise} axios promise
 */
export const getInvoices = (params = {}) => {

/**
 * 获取单个支付记录详情
 * @param {String} paymentId - 支付ID
 * @returns {Promise} axios promise
 */
export const getPaymentDetail = (paymentId) => {

/**
 * 获取单个发票详情
 * @param {String} invoiceId - 发票ID
 * @returns {Promise} axios promise
 */
export const getInvoiceDetail = (invoiceId) => {

/**
 * 下载发票PDF
 * @param {String} invoiceId - 发票ID
 * @returns {Promise} axios promise
 */
export const downloadInvoice = (invoiceId) => {
  return axios.get(`${API_BASE_URL}/invoices/${invoiceId}/download`, {
    responseType: 'blob',
    headers: {
      'Authorization': `Bearer ${getToken()}`
    }
  });
};
  return axios.get(`${API_BASE_URL}/invoices/${invoiceId}`, {
    headers: {
      'Authorization': `Bearer ${getToken()}`
    }
  });
};
  return axios.get(`${API_BASE_URL}/payments/${paymentId}`, {
    headers: {
      'Authorization': `Bearer ${getToken()}`
    }
  });
};
  return axios.get(`${API_BASE_URL}/invoices`, {
    params,
    headers: {
      'Authorization': `Bearer ${getToken()}`
    }
  });
};