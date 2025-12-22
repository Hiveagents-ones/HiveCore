import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 获取课程列表
export const getCourses = async () => {
  try {
    const response = await apiClient.get('/courses');
    return response.data;
  } catch (error) {
    console.error('Error fetching courses:', error);
    throw error;
  }
};

// 获取单个课程详情
export const getCourse = async (courseId) => {
  try {
    const response = await apiClient.get(`/courses/${courseId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching course:', error);
    throw error;
  }
};

// 预约课程
export const bookCourse = async (courseId, userId) => {
  try {
    const response = await apiClient.post(`/courses/${courseId}/book`, {
      user_id: userId,
    });
    return response.data;
  } catch (error) {
    console.error('Error booking course:', error);
    throw error;
  }
};

// 取消预约课程
export const cancelBooking = async (courseId, userId) => {
  try {
    const response = await apiClient.post(`/courses/${courseId}/cancel`, {
      user_id: userId,
    });
    return response.data;
  } catch (error) {
    console.error('Error canceling booking:', error);
    throw error;
  }
};

// 获取用户的预约记录
export const getUserBookings = async (userId) => {
  try {
    const response = await apiClient.get(`/users/${userId}/bookings`);
    return response.data;
  } catch (error) {
    console.error('Error fetching user bookings:', error);
    throw error;
  }
};

export default {
  getCourses,
  getCourse,
  bookCourse,
  cancelBooking,
  getUserBookings,
};