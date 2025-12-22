import axios from 'axios';
import { useAuthStore } from '../stores/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const DEFAULT_PER_PAGE = 20;

/**
 * 获取教练排班列表
 * @param {Object} params - 查询参数
 * @returns {Promise} Axios Promise
 */
export const getCoachSchedules = async (params = { page: 1, per_page: DEFAULT_PER_PAGE }) => {
  const authStore = useAuthStore();
  try {
    const response = await axios.get(`${API_BASE_URL}/api/v1/coaches/schedules`, {
      params: {
        ...params,
        per_page: params.per_page || DEFAULT_PER_PAGE
      },
      headers: {
        Authorization: `Bearer ${authStore.token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching coach schedules:', error);
    throw error;
  }
};

/**
 * 创建教练排班
 * @param {Object} scheduleData - 排班数据
 * @returns {Promise} Axios Promise
 */
export const createCoachSchedule = async (scheduleData) => {
  const authStore = useAuthStore();
  try {
    const response = await axios.post(`${API_BASE_URL}/api/v1/coaches/schedules`, scheduleData, {
      headers: {
        Authorization: `Bearer ${authStore.token}`,
        'Content-Type': 'application/json'
      }
    });
    return response.data;
  } catch (error) {
    console.error('Error creating coach schedule:', error);
    throw error;
  }
};

/**
 * 更新教练排班
 * @param {number} scheduleId - 排班ID
 * @param {Object} updateData - 更新数据
 * @returns {Promise} Axios Promise
 */
export const updateCoachSchedule = async (scheduleId, updateData) => {
  const authStore = useAuthStore();
  try {
    const response = await axios.put(`${API_BASE_URL}/api/v1/coaches/schedules/${scheduleId}`, updateData, {
      headers: {
        Authorization: `Bearer ${authStore.token}`,
        'Content-Type': 'application/json'
      }
    });
    return response.data;
  } catch (error) {
    console.error('Error updating coach schedule:', error);
    throw error;
  }
};

/**
 * 删除教练排班
 * @param {number} scheduleId - 排班ID
 * @returns {Promise} Axios Promise
 */
export const deleteCoachSchedule = async (scheduleId) => {


/**
 * 检查排班冲突
 * @param {Object} scheduleData - 排班数据
 * @returns {Promise} Axios Promise
 */
export const checkScheduleConflict = async (scheduleData) => {
  const authStore = useAuthStore();
  try {
    const response = await axios.post(`${API_BASE_URL}/api/v1/coaches/schedules/check-conflict`, scheduleData, {
      headers: {
        Authorization: `Bearer ${authStore.token}`,
        'Content-Type': 'application/json'
      }
    });
    return response.data;
  } catch (error) {
    console.error('Error checking schedule conflict:', error);
    throw error;
  }
};
  const authStore = useAuthStore();
  try {
    const response = await axios.delete(`${API_BASE_URL}/api/v1/coaches/schedules/${scheduleId}`, {
      headers: {
        Authorization: `Bearer ${authStore.token}`
      }
    });
    return response.data;
  } catch (error) {
    console.error('Error deleting coach schedule:', error);
    throw error;
  }
};