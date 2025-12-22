import axios from 'axios';
import { useAuthStore } from '../stores/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/**
 * 获取课程列表
 * @param {Object} params - 查询参数
 * @param {string} params.startDate - 开始日期
 * @param {string} params.endDate - 结束日期
 * @param {number} params.coachId - 教练ID
 * @returns {Promise<Array>} 课程列表
 */
export const getCourses = async (params = {}) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/courses`, {
      params,
      headers: {
        Authorization: `Bearer ${useAuthStore().token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error('获取课程列表失败:', error);
    throw error;
  }
};

/**
 * 预约课程
 * @param {number} courseId - 课程ID
 * @returns {Promise<Object>} 预约结果
 */
export const bookCourse = async (courseId) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/courses/book`,
      { course_id: courseId },
      {
        headers: {
          Authorization: `Bearer ${useAuthStore().token}`
        }
      }
    );
    return response.data;
  } catch (error) {
    console.error('预约课程失败:', error);
    throw error;
  }
};

/**
 * 取消预约
 * @param {number} courseId - 课程ID
 * @returns {Promise<Object>} 取消结果
 */
export const cancelBooking = async (courseId) => {
  try {
    const response = await axios.delete(`${API_BASE_URL}/courses/book`, {
      data: { course_id: courseId },
      headers: {
        Authorization: `Bearer ${useAuthStore().token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error('取消预约失败:', error);
    throw error;
  }
};