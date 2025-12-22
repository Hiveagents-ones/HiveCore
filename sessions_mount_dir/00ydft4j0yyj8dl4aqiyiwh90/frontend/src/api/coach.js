import axios from 'axios';

const API_BASE_URL = '/api/v1';
const ADMIN_API_BASE_URL = '/api/v1/admin';
const COACH_API_BASE_URL = '/api/v1/coach';

/**
 * 获取所有教练列表
 * @returns {Promise<Array>} 教练列表
 */
export const getCoaches = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/coaches`);
    return response.data;
  } catch (error) {
    console.error('Error fetching coaches:', error);
    throw error;
  }
};

/**
 * 管理员获取所有教练列表
 * @returns {Promise<Array>} 教练列表
 */
export const adminGetCoaches = async () => {
  try {
    const response = await axios.get(`${ADMIN_API_BASE_URL}/coaches`);
    return response.data;
  } catch (error) {
    console.error('Error fetching coaches as admin:', error);
    throw error;
  }
};

/**
 * 创建新教练
 * @param {Object} coachData 教练数据
 * @returns {Promise<Object>} 新创建的教练
 */
export const createCoach = async (coachData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/coaches`, coachData);
    return response.data;
  } catch (error) {
    console.error('Error creating coach:', error);
    throw error;
  }
};

/**
 * 管理员创建新教练
 * @param {Object} coachData 教练数据
 * @returns {Promise<Object>} 新创建的教练
 */
export const adminCreateCoach = async (coachData) => {
  try {
    const response = await axios.post(`${ADMIN_API_BASE_URL}/coaches`, coachData);
    return response.data;
  } catch (error) {
    console.error('Error creating coach as admin:', error);
    throw error;
  }
};

/**
 * 更新教练信息
 * @param {number} coachId 教练ID
 * @param {Object} updateData 更新数据
 * @returns {Promise<Object>} 更新后的教练信息
 */
export const updateCoach = async (coachId, updateData) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/coaches/${coachId}`, updateData);
    return response.data;
  } catch (error) {
    console.error('Error updating coach:', error);
    throw error;
  }
};

/**
 * 管理员更新教练信息
 * @param {number} coachId 教练ID
 * @param {Object} updateData 更新数据
 * @returns {Promise<Object>} 更新后的教练信息
 */
export const adminUpdateCoach = async (coachId, updateData) => {
  try {
    const response = await axios.put(`${ADMIN_API_BASE_URL}/coaches/${coachId}`, updateData);
    return response.data;
  } catch (error) {
    console.error('Error updating coach as admin:', error);
    throw error;
  }
};

/**
 * 删除教练
 * @param {number} coachId 教练ID
 * @returns {Promise<void>}
 */
export const deleteCoach = async (coachId) => {
  try {
    await axios.delete(`${API_BASE_URL}/coaches/${coachId}`);
  } catch (error) {
    console.error('Error deleting coach:', error);
    throw error;
  }
};

/**
 * 管理员删除教练
 * @param {number} coachId 教练ID
 * @returns {Promise<void>}
 */
export const adminDeleteCoach = async (coachId) => {
  try {
    await axios.delete(`${ADMIN_API_BASE_URL}/coaches/${coachId}`);
  } catch (error) {
    console.error('Error deleting coach as admin:', error);
    throw error;
  }
};

/**
 * 获取教练排班信息
 * @param {number} coachId 教练ID
 * @returns {Promise<Array>} 排班信息
 */
export const getCoachSchedules = async (coachId) => {
  try {
    const response = await axios.get(`${COACH_API_BASE_URL}/${coachId}/schedules`);
    return response.data;
  } catch (error) {
    console.error('Error fetching coach schedules:', error);
    throw error;
  }
};

/**
 * 管理员获取教练排班信息
 * @param {number} coachId 教练ID
 * @returns {Promise<Array>} 排班信息
 */
export const adminGetCoachSchedules = async (coachId) => {
  try {
    const response = await axios.get(`${ADMIN_API_BASE_URL}/coaches/${coachId}/schedules`);
    return response.data;
  } catch (error) {
    console.error('Error fetching coach schedules as admin:', error);
    throw error;
  }
};

/**
 * 更新教练排班信息
 * @param {number} coachId 教练ID
 * @param {Array} schedules 排班数据
 * @returns {Promise<Object>}
 */
export const updateCoachSchedules = async (coachId, schedules) => {
  try {
    const response = await axios.post(`${COACH_API_BASE_URL}/${coachId}/schedules`, { schedules });
    return response.data;
  } catch (error) {
    console.error('Error updating coach schedules:', error);
    throw error;
  }
};

/**
 * 管理员更新教练排班信息
 * @param {number} coachId 教练ID
 * @param {Array} schedules 排班数据
 * @returns {Promise<Object>}
 */
export const adminUpdateCoachSchedules = async (coachId, schedules) => {
  try {
    const response = await axios.post(`${ADMIN_API_BASE_URL}/coaches/${coachId}/schedules`, { schedules });
    return response.data;
  } catch (error) {
    console.error('Error updating coach schedules as admin:', error);
    throw error;
  }
};
