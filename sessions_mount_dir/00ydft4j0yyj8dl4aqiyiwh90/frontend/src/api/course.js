import axios from 'axios';

const API_BASE_URL = '/api/v1';

/**
 * 获取所有课程列表
 * @returns {Promise<Array>} 课程列表
 */
export const getCourses = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/courses`);
    if (!response.data || !response.data.data) {
      throw new Error('Invalid response data');
    }
    return response.data;
  } catch (error) {
    console.error('Error fetching courses:', error);
    throw error;
  }
};

/**
 * 获取单个课程详情
 * @param {number} courseId 课程ID
 * @returns {Promise<Object>} 课程详情
 */
export const getCourseById = async (courseId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/courses/${courseId}`);
    if (!response.data || !response.data.data) {
      throw new Error('Invalid course data');
    }
    return response.data;
  } catch (error) {
    console.error(`Error fetching course with ID ${courseId}:`, error);
    throw error;
  }
};

/**
 * 创建新课程
 * @param {Object} courseData 课程数据
 * @returns {Promise<Object>} 创建后的课程
 */
export const createCourse = async (courseData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/courses`, courseData);
    if (!response.data || !response.data.data) {
      throw new Error('Failed to create course');
    }
    return response.data;
  } catch (error) {
    console.error('Error creating course:', error);
    throw error;
  }
};

/**
 * 更新课程信息
 * @param {number} courseId 课程ID
 * @param {Object} courseData 更新的课程数据
 * @returns {Promise<Object>} 更新后的课程
 */
export const updateCourse = async (courseId, courseData) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/courses/${courseId}`, courseData);
    if (!response.data || !response.data.data) {
      throw new Error('Failed to update course');
    }
    return response.data;
  } catch (error) {
    console.error(`Error updating course with ID ${courseId}:`, error);
    throw error;
  }
};

/**
 * 删除课程
 * @param {number} courseId 课程ID
 * @returns {Promise<void>}
 */
export const deleteCourse = async (courseId) => {
  try {
    await axios.delete(`${API_BASE_URL}/courses/${courseId}`);
  } catch (error) {
    console.error(`Error deleting course with ID ${courseId}:`, error);
    throw error;
  }
};
