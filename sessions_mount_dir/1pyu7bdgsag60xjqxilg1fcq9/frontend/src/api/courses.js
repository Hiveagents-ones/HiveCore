import axios from 'axios';

const API_BASE_URL = '/api/v1';

/**
 * 获取所有课程列表
 * @returns {Promise<Array>} 课程列表
 */
export const getCourses = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/courses`);
    return response.data;
  } catch (error) {
    console.error('获取课程列表失败:', error);
    throw error;
  }
};

/**
 * 获取单个课程详情
 * @param {number} id 课程ID
 * @returns {Promise<Object>} 课程详情
 */
export const getCourseById = async (id) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/courses/${id}`);
    return response.data;
  } catch (error) {
    console.error('获取课程详情失败:', error);
    throw error;
  }
};

/**
 * 创建新课程预约
 * @param {Object} courseData 课程数据
 * @returns {Promise<Object>} 创建的课程
 */
export const createCourse = async (courseData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/courses`, courseData);
    return response.data;
  } catch (error) {
    console.error('创建课程失败:', error);
    throw error;
  }
};

/**
 * 更新课程信息
 * @param {number} id 课程ID
 * @param {Object} courseData 更新的课程数据
 * @returns {Promise<Object>} 更新后的课程
 */
export const updateCourse = async (id, courseData) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/courses/${id}`, courseData);
    return response.data;
  } catch (error) {
    console.error('更新课程失败:', error);
    throw error;
  }
};

/**
 * 删除课程
 * @param {number} id 课程ID
 * @returns {Promise<void>}
 */
export const deleteCourse = async (id) => {
  try {
    await axios.delete(`${API_BASE_URL}/courses/${id}`);
  } catch (error) {
    console.error('删除课程失败:', error);
    throw error;
  }
};

/**
 * 获取教练排班信息
 * @returns {Promise<Array>} 教练排班列表
 */
export const getCoachSchedules = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/coaches`);
    return response.data;
  } catch (error) {
    console.error('获取教练排班失败:', error);
    throw error;
  }
};