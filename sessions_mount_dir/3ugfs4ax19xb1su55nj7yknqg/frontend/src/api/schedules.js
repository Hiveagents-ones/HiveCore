import axios from 'axios';

const API_BASE_URL = '/api/v1';

const SCHEDULE_CACHE_KEY = 'coach_schedules_cache';

/**
 * 获取教练排班列表
 * @param {number} coachId - 教练ID
 * @returns {Promise<Array>} - 排班列表
 */
export const getCoachSchedules = async (coachId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/coaches/${coachId}/schedule`);
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
      `${API_BASE_URL}/coaches/${coachId}/schedule`,
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
      `${API_BASE_URL}/coaches/${coachId}/schedule/${scheduleId}`,
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

/**
 * 批量创建教练排班
 * @param {number} coachId - 教练ID
 * @param {Array<Object>} schedules - 排班数据数组
 * @returns {Promise<Array>} - 创建的排班列表
 */
export const batchCreateSchedules = async (coachId, schedules) => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/coaches/${coachId}/schedules/batch`,
      { schedules }
    );
    return response.data;
  } catch (error) {
    console.error('批量创建排班失败:', error);
    throw error;
  }
};

/**
 * 获取教练可用时间段
 * @param {number} coachId - 教练ID
 * @param {string} date - 查询日期 (YYYY-MM-DD)
 * @returns {Promise<Array>} - 可用时间段列表
 */
export const getCoachAvailableSlots = async (coachId, date) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/coaches/${coachId}/available-slots`,
      { params: { date } }
    );
    return response.data;
  } catch (error) {
    console.error('获取可用时间段失败:', error);
    throw error;
  }
};

/**
 * 获取教练排班缓存
 * @param {number} coachId - 教练ID
 * @returns {Array|null} - 缓存的排班数据
 */
export const getCachedSchedules = (coachId) => {
  const cache = localStorage.getItem(SCHEDULE_CACHE_KEY);
  if (cache) {
    const parsed = JSON.parse(cache);
    return parsed[coachId] || null;
  }
  return null;
};

/**
 * 缓存教练排班数据
 * @param {number} coachId - 教练ID
 * @param {Array} schedules - 排班数据
 */
export const cacheSchedules = (coachId, schedules) => {
  let cache = {};
  const existing = localStorage.getItem(SCHEDULE_CACHE_KEY);
  if (existing) {
    cache = JSON.parse(existing);
  }
  cache[coachId] = schedules;
  localStorage.setItem(SCHEDULE_CACHE_KEY, JSON.stringify(cache));
};
  try {
    await axios.delete(`${API_BASE_URL}/coaches/${coachId}/schedule/${scheduleId}`);
  } catch (error) {
    console.error('删除教练排班失败:', error);
    throw error;
  }
};