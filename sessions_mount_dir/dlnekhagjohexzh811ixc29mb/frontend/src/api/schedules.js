import axios from 'axios';

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || '/api/v1';

/**
 * 获取教练排班列表
 * @param {number} coachId - 教练ID
 * @returns {Promise<Array>} - 排班列表
 */
export const getCoachSchedules = async (coachId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/coaches/${coachId}/schedules`);
    return response.data;
  } catch (error) {
    console.error('获取教练排班失败:', error);
    throw error;
  }
};

/**
 * 创建教练排班
 * @param {number} coachId - 教练ID
 * @param {Object} scheduleData - 排班数据
 * @param {string} scheduleData.day_of_week - 星期几
 * @param {string} scheduleData.start_hour - 开始时间
 * @param {string} scheduleData.end_hour - 结束时间
 * @returns {Promise<Object>} - 创建的排班数据
 */
export const createCoachSchedule = async (coachId, scheduleData) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/coaches/${coachId}/schedules`,
      scheduleData
    );
    return response.data;
  } catch (error) {
    console.error('创建教练排班失败:', error);
    throw error;
  }
};

/**
 * 更新教练排班
 * @param {number} coachId - 教练ID
 * @param {number} scheduleId - 排班ID
 * @param {Object} scheduleData - 更新的排班数据
 * @returns {Promise<Object>} - 更新后的排班数据
 */
export const updateCoachSchedule = async (coachId, scheduleId, scheduleData) => {
  try {
    const response = await axios.put(
      `${API_BASE_URL}/coaches/${coachId}/schedules/${scheduleId}`,
      scheduleData
    );
    return response.data;
  } catch (error) {
    console.error('更新教练排班失败:', error);
    throw error;
  }
};

/**
 * 删除教练排班
 * @param {number} coachId - 教练ID
 * @param {number} scheduleId - 排班ID
 * @returns {Promise<void>}
 */
export const deleteCoachSchedule = async (coachId, scheduleId) => {
  try {
    await axios.delete(`${API_BASE_URL}/coaches/${coachId}/schedules/${scheduleId}`);
  } catch (error) {
    console.error('删除教练排班失败:', error);
    throw error;
  }
};