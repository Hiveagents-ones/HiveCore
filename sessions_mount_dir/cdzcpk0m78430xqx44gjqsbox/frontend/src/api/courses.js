import axios from 'axios';
import { encryptData } from '@/utils/crypto';

const API_BASE_URL = '/api/v1';

/**
 * 获取课程列表
 * @returns {Promise<Array>} 课程列表
 */
export const getCourses = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/courses`, {
      headers: {
        'X-Encrypted': 'true'
      }
    });
    return response.data;
  } catch (error) {
    console.error('获取课程列表失败:', error);
    throw error;
  }
};

/**
 * 获取课程详情
 * @param {number} courseId 课程ID
 * @returns {Promise<Object>} 课程详情
 */
export const getCourseDetails = async (courseId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/courses/${courseId}`, {
      headers: {
        'X-Encrypted': 'true'
      }
    });
    return response.data;
  } catch (error) {
    console.error('获取课程详情失败:', error);
    throw error;
  }
};

/**
 * 预约课程
 * @param {number} courseId 课程ID
 * @param {number} memberId 会员ID
 * @returns {Promise<Object>} 预约结果
 */
export const bookCourse = async (courseId, memberId) => {
  try {
    const encryptedData = encryptData({ member_id: memberId });
    const response = await axios.post(`${API_BASE_URL}/courses/${courseId}/bookings`, encryptedData, {
      headers: {
        'X-Encrypted': 'true'
      }
    });
    return response.data;
  } catch (error) {
    console.error('预约课程失败:', error);
    throw error;
  }
};

/**
 * 取消预约
 * @param {number} bookingId 预约ID
 * @returns {Promise<Object>} 取消结果
 */
export const cancelBooking = async (bookingId) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/courses/bookings/${bookingId}`, {
      headers: {
        'X-Encrypted': 'true'
      }
    });
    return response.data;
  } catch (error) {
    console.error('取消预约失败:', error);
    throw error;
  }
};

/**
 * 获取课程预约人数
 * @param {number} courseId 课程ID
 * @returns {Promise<number>} 预约人数
 */
export const getBookingCount = async (courseId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/courses/${courseId}/bookings/count`, {
      headers: {
        'X-Encrypted': 'true'
      }
    });
    return response.data.count;
  } catch (error) {
    console.error('获取预约人数失败:', error);
    throw error;
  }
};