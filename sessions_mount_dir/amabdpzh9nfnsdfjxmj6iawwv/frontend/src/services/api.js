import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 用户注册接口
export const registerUser = async (userData) => {
  try {
    const response = await apiClient.post('/auth/register', userData);
    return response;
  } catch (error) {
    throw error.response?.data || error;
  }
};

// 用户登录接口
export const loginUser = async (credentials) => {
  try {
    const response = await apiClient.post('/auth/login', credentials);
    return response;
  } catch (error) {
    throw error.response?.data || error;
  }
};

// 获取用户信息接口
export const getUserInfo = async () => {
  try {
    const response = await apiClient.get('/user/me');
    return response;
  } catch (error) {
    throw error.response?.data || error;
  }
};

// 更新用户信息接口
export const updateUserInfo = async (userData) => {
  try {
    const response = await apiClient.put('/user/me', userData);
    return response;
  } catch (error) {
    throw error.response?.data || error;
  }
};

// 获取会员信息接口
export const getMembershipInfo = async () => {
  try {
    const response = await apiClient.get('/membership/info');
    return response;
  } catch (error) {
    throw error.response?.data || error;
  }
};

// 获取课程列表接口
export const getCourseList = async (params = {}) => {
  try {
    const response = await apiClient.get('/courses', { params });
    return response;
  } catch (error) {
    throw error.response?.data || error;
  }
};

// 预约课程接口
export const bookCourse = async (courseId) => {
  try {
    const response = await apiClient.post(`/courses/${courseId}/book`);
    return response;
  } catch (error) {
    throw error.response?.data || error;
  }
};

// 取消预约接口
export const cancelBooking = async (bookingId) => {
  try {
    const response = await apiClient.delete(`/bookings/${bookingId}`);
    return response;
  } catch (error) {
    throw error.response?.data || error;
  }
};

// 获取预约记录接口
export const getBookingHistory = async (params = {}) => {
  try {
    const response = await apiClient.get('/bookings', { params });
    return response;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export default apiClient;