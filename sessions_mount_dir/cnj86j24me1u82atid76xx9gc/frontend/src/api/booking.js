import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

/**
 * 获取所有预约记录
 * @returns {Promise} 预约记录列表
 */
export const getAllBookings = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/bookings`);
    return response.data;
  } catch (error) {
    console.error('Error fetching bookings:', error);
    throw error;
  }
};

/**
 * 根据用户ID获取预约记录
 * @param {string} userId - 用户ID
 * @returns {Promise} 用户的预约记录列表
 */
export const getBookingsByUser = async (userId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/bookings/user/${userId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching user bookings:', error);
    throw error;
  }
};

/**
 * 创建新预约
 * @param {Object} bookingData - 预约数据
 * @param {string} bookingData.course_id - 课程ID
 * @param {string} bookingData.user_id - 用户ID
 * @returns {Promise} 创建的预约记录
 */
export const createBooking = async (bookingData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/bookings`, bookingData);
    return response.data;
  } catch (error) {
    console.error('Error creating booking:', error);
    throw error;
  }
};

/**
 * 取消预约
 * @param {string} bookingId - 预约ID
 * @returns {Promise} 取消结果
 */
export const cancelBooking = async (bookingId) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/bookings/${bookingId}`);
    return response.data;
  } catch (error) {
    console.error('Error cancelling booking:', error);
    throw error;
  }
};

/**
 * 获取课程预约状态
 * @param {string} courseId - 课程ID
 * @returns {Promise} 课程预约状态信息
 */
export const getCourseBookingStatus = async (courseId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/courses/${courseId}/booking-status`);
    return response.data;
  } catch (error) {
    console.error('Error fetching course booking status:', error);
    throw error;
  }
};

/**
 * 检查用户是否已预约某课程
 * @param {string} courseId - 课程ID
 * @param {string} userId - 用户ID
 * @returns {Promise} 预约状态
 */
export const checkUserBooking = async (courseId, userId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/bookings/check`, {
      params: { course_id: courseId, user_id: userId }
    });
    return response.data;
  } catch (error) {
    console.error('Error checking user booking:', error);
    throw error;
  }
};
