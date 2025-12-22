import axios from 'axios';
import { retry } from '../utils/retry';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * 获取所有课程列表
 * @returns {Promise<Array>} 课程列表
 */
export const getCourses = async () => {
  try {
    const response = await retry(
      () => axios.get(`${API_BASE_URL}/api/v1/courses`),
      {
        retries: 3,
        retryDelay: 1000,
        retryCondition: (error) => error.response?.status >= 500
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error fetching courses:', error);
    throw error;
  }
};

/**
 * 创建新课程预约
 * @param {Object} courseData - 课程数据
 * @param {string} courseData.name - 课程名称
 * @param {string} courseData.schedule - 课程时间
 * @param {number} courseData.coach_id - 教练ID
 * @param {number} courseData.max_members - 最大人数
 * @returns {Promise<Object>} 创建的课程数据
 */
export const createCourse = async (courseData) => {
  try {
    const response = await retry(
      () => axios.post(`${API_BASE_URL}/api/v1/courses`, courseData),
      {
        retries: 3,
        retryDelay: 1000,
        retryCondition: (error) => error.response?.status >= 500
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error creating course:', error);
    throw error;
  }
};

/**
 * 获取特定课程详情
 * @param {number} courseId - 课程ID
 * @returns {Promise<Object>} 课程详情
 */
export const getCourseById = async (courseId) => {
  try {
    const response = await retry(
      () => axios.get(`${API_BASE_URL}/api/v1/courses/${courseId}`),
      {
        retries: 3,
        retryDelay: 1000,
        retryCondition: (error) => error.response?.status >= 500
      }
    );
    return response.data;
  } catch (error) {
    console.error(`Error fetching course with ID ${courseId}:`, error);
    throw error;
  }
};

export default {
  getCourses,
  createCourse,
  getCourseById
};