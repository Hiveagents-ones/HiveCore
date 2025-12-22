import axios from 'axios';
import { useAuthStore } from '@/stores/auth';
import { retry } from '@/utils/retry';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// 重试配置常量
const DEFAULT_RETRY_CONFIG = {
  maxAttempts: 3,
  delay: 1000,
  retryOn: [502, 503, 504, 408, 429],
  shouldRetry: (error) => {
    // 对于网络错误或特定状态码进行重试
    return !error.response || DEFAULT_RETRY_CONFIG.retryOn.includes(error.response?.status);
  },
  onRetry: (attempt, error) => {
    console.warn(`请求失败，正在进行第${attempt}次重试...`, error.message);
  },
  onMaxRetryExceeded: (error) => {
    console.error('已达到最大重试次数:', error.message);
    throw error;
  }
};

const BOOKING_RETRY_CONFIG = {
  maxAttempts: 2,
  delay: 500,
  retryOn: [502, 503, 504, 429],
  shouldRetry: (error) => {
    // 预约操作只对特定错误重试
    return !error.response || BOOKING_RETRY_CONFIG.retryOn.includes(error.response?.status);
  },
  onRetry: (attempt, error) => {
    console.warn(`预约请求失败，正在进行第${attempt}次重试...`, error.message);
  },
  onMaxRetryExceeded: (error) => {
    console.error('预约操作已达到最大重试次数:', error.message);
    throw error;
  }
};

// 创建带并发控制的axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000, // 增加超时时间
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
    'Accept': 'application/json'
  },
  withCredentials: true,
  validateStatus: function (status) {
    // 对于2xx和特定状态码不抛出错误
    return (status >= 200 && status < 300) || [401, 403, 404, 409, 410, 429].includes(status);
  }
});

// 请求拦截器 - 添加认证token
apiClient.interceptors.request.use(config => {
  const authStore = useAuthStore();
  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`;
  }
  return config;
});

// 响应拦截器 - 统一错误处理
apiClient.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response) {
      const { status, data } = error.response;
      const errorMessage = data?.message || `Request failed with status code ${status}`;
      
      // 对于特定状态码进行特殊处理
      if (status === 401) {
        const authStore = useAuthStore();
        authStore.logout();
        window.location.href = '/login';
      } else if (status === 429) {
        throw new Error('请求过于频繁，请稍后再试');
      } else if (status === 403) {
        throw new Error('无权限执行此操作');
      } else if (status === 404) {
        throw new Error('请求的资源不存在');
      } else if (status >= 500) {
        throw new Error('服务器内部错误，请稍后再试');
      }
      
      throw new Error(errorMessage);
    } else if (error.request) {
      throw new Error('服务器无响应，请检查网络连接');
    } else {
      throw new Error(`请求配置错误: ${error.message}`);
    }
  }
);

/**
 * 获取所有课程列表
 * @returns {Promise<Array>} 课程列表
 */
/**
 * 获取所有课程列表
 * @returns {Promise<Array>} 课程列表
 * @throws {Error} 请求失败时抛出错误
 */
export const getCourses = async () => {
  try {
    const response = await retry(() => apiClient.get('/courses'), DEFAULT_RETRY_CONFIG);
    return response.data || [];
  } catch (error) {
    console.error('获取课程列表失败:', error);
    throw new Error(`获取课程列表失败: ${error.message}`);
  }
};

/**
 * 获取课程时间表
 * @returns {Promise<Array>} 课程时间表
 */
/**
 * 获取课程时间表
 * @returns {Promise<Array>} 课程时间表
 * @throws {Error} 请求失败时抛出错误
 */
export const getCourseSchedule = async () => {
  try {
    const response = await retry(() => apiClient.get('/courses/schedule'), DEFAULT_RETRY_CONFIG);
    return response.data || [];
  } catch (error) {
    console.error('获取课程时间表失败:', error);
    throw new Error(`获取课程时间表失败: ${error.message}`);
  }
};

/**
 * 预约课程
 * @param {number} courseId 课程ID
 * @param {number} memberId 会员ID
 * @returns {Promise<Object>} 预约结果
 */
/**
 * 预约课程
 * @param {number} courseId 课程ID
 * @param {number} memberId 会员ID
 * @returns {Promise<Object>} 预约结果
 * @throws {Error} 请求失败时抛出错误
 */
export const bookCourse = async (courseId, memberId) => {
  try {
    const response = await retry(
      () => apiClient.post(`/courses/${courseId}/bookings`, { member_id: memberId }),
      BOOKING_RETRY_CONFIG
    );
    
    if (response.status === 409) {
      throw new Error('该课程已预约满或时间冲突');
    }
    
    return response.data;
  } catch (error) {
    console.error('课程预约失败:', error);
    throw error;
  }
};

/**
 * 取消课程预约
 * @param {number} bookingId 预约ID
 * @returns {Promise<Object>} 取消结果
 */
/**
 * 取消课程预约
 * @param {number} bookingId 预约ID
 * @returns {Promise<Object>} 取消结果
 * @throws {Error} 请求失败时抛出错误
 */
export const cancelBooking = async (bookingId) => {
  try {
    const response = await retry(
      () => apiClient.delete(`/courses/bookings/${bookingId}`),
      BOOKING_RETRY_CONFIG
    );

    if (response.status === 410) {
      throw new Error('无法取消已开始的课程');
    }

    return response.data;
  } catch (error) {
    console.error('取消预约失败:', error);
    throw new Error(`取消预约失败: ${error.message}`);
  }
};

/**
 * 获取会员的课程预约记录
 * @param {number} memberId 会员ID
 * @returns {Promise<Array>} 预约记录列表
 * @throws {Error} 请求失败时抛出错误
 */
export const getMemberBookings = async (memberId) => {
  try {
    const response = await retry(
      () => apiClient.get(`/members/${memberId}/bookings`),
      DEFAULT_RETRY_CONFIG
    );
    return response.data || [];
  } catch (error) {
    console.error('获取会员预约记录失败:', error);
    throw new Error(`获取会员预约记录失败: ${error.message}`);
  }
};
  try {
    const response = await retry(
      () => apiClient.delete(`/courses/bookings/${bookingId}`),
      BOOKING_RETRY_CONFIG
    );
    
    if (response.status === 410) {
      throw new Error('无法取消已开始的课程');
    }
    
    return response.data;
  } catch (error) {
    console.error('取消预约失败:', error);
    throw error;
  }
};