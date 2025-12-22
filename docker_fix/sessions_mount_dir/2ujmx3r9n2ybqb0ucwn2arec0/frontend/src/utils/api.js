import axios from 'axios';
import { ElMessage } from 'element-plus';
import router from '../router';

// 创建axios实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 从localStorage获取token
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 生成或传递Trace ID
    let traceId = config.headers['X-Trace-ID'] || generateTraceId();
    config.headers['X-Trace-ID'] = traceId;

    // 记录请求日志
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
      traceId,
      data: config.data,
      params: config.params,
    });

    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    const traceId = response.headers['x-trace-id'];
    console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, {
      traceId,
      status: response.status,
      data: response.data,
    });

    // 检查业务状态码
    if (response.data && response.data.code !== undefined && response.data.code !== 0) {
      const message = response.data.message || '请求失败';
      ElMessage.error(message);
      return Promise.reject(new Error(message));
    }

    return response.data;
  },
  (error) => {
    const traceId = error.response?.headers['x-trace-id'];
    console.error(`[API Response Error] ${error.config?.method?.toUpperCase()} ${error.config?.url}`, {
      traceId,
      status: error.response?.status,
      data: error.response?.data,
    });

    // 统一错误处理
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;
      let message = '请求失败';

      switch (status) {
        case 400:
          message = data?.detail || '请求参数错误';
          break;
        case 401:
          message = '未授权，请重新登录';
          localStorage.removeItem('token');
          router.push('/login');
          break;
        case 403:
          message = '拒绝访问';
          break;
        case 404:
          message = '请求资源不存在';
          break;
        case 429:
          message = '请求过于频繁，请稍后再试';
          break;
        case 500:
          message = '服务器内部错误';
          break;
        case 502:
          message = '网关错误';
          break;
        case 503:
          message = '服务不可用';
          break;
        default:
          message = data?.detail || `请求失败 (${status})`;
      }

      ElMessage.error(message);
    } else if (error.request) {
      ElMessage.error('网络错误，请检查网络连接');
    } else {
      ElMessage.error('请求配置错误');
    }

    return Promise.reject(error);
  }
);

// 生成Trace ID
function generateTraceId() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// API方法封装
export const apiRequest = {
  get(url, params = {}, config = {}) {
    return api.get(url, { params, ...config });
  },

  post(url, data = {}, config = {}) {
    return api.post(url, data, config);
  },

  put(url, data = {}, config = {}) {
    return api.put(url, data, config);
  },

  delete(url, config = {}) {
    return api.delete(url, config);
  },

  patch(url, data = {}, config = {}) {
    return api.patch(url, data, config);
  },

  // 文件上传
  upload(url, formData, onProgress) {
    return api.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress,
    });
  },

  // 文件下载
  download(url, params = {}) {
    return api.get(url, {
      params,
      responseType: 'blob',
    });
  },
};

// 会员相关API
export const membershipApi = {
  // 获取会员状态
  getMembershipStatus() {
    return apiRequest.get('/membership/status');
  },

  // 获取会员套餐列表
  getMembershipPlans() {
    return apiRequest.get('/membership/plans');
  },

  // 创建续费订单
  createRenewalOrder(planId) {
    return apiRequest.post('/membership/renewal', { plan_id: planId });
  },

  // 获取订单状态
  getOrderStatus(orderId) {
    return apiRequest.get(`/payment/orders/${orderId}`);
  },

  // 取消订单
  cancelOrder(orderId) {
    return apiRequest.delete(`/payment/orders/${orderId}`);
  },
};

// 支付相关API
export const paymentApi = {
  // 创建支付订单
  createPayment(orderId, paymentMethod) {
    return apiRequest.post('/payment/create', {
      order_id: orderId,
      payment_method: paymentMethod,
    });
  },

  // 获取支付状态
  getPaymentStatus(paymentId) {
    return apiRequest.get(`/payment/status/${paymentId}`);
  },

  // 微信支付
  wechatPay(orderId) {
    return apiRequest.post('/payment/wechat', { order_id: orderId });
  },

  // 支付宝支付
  alipay(orderId) {
    return apiRequest.post('/payment/alipay', { order_id: orderId });
  },
};

export default api;