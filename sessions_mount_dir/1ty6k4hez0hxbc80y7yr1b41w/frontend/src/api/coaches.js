import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * 获取教练排班列表
 * @param {Object} params - 查询参数
 * @returns {Promise} Axios Promise
 */
/**
 * 获取教练排班列表
 * @param {Object} params - 查询参数
 * @param {number} [params.coach_id] - 教练ID
 * @param {string} [params.start_date] - 开始日期
 * @param {string} [params.end_date] - 结束日期
 * @returns {Promise} Axios Promise
 */
export const getCoachSchedules = (params = {}) => {
  return axios.get(`${API_BASE_URL}/api/v1/coaches/schedule`, { params });
};

/**
 * 创建教练排班
 * @param {Object} data - 排班数据
 * @returns {Promise} Axios Promise
 */
export const createCoachSchedule = (data) => {
  return axios.post(`${API_BASE_URL}/api/v1/coaches/schedule`, data);
};

/**
 * 更新教练排班
 * @param {number} id - 排班ID
 * @param {Object} data - 更新数据
 * @returns {Promise} Axios Promise
 */
export const updateCoachSchedule = (id, data) => {
  return axios.put(`${API_BASE_URL}/api/v1/coaches/schedule/${id}`, data);
};

/**
 * 获取单个教练的排班
 * @param {number} coachId - 教练ID
 * @returns {Promise} Axios Promise
 */
/**
 * 获取单个教练的排班
 * @param {number} coachId - 教练ID
 * @param {string} [startDate] - 开始日期
 * @param {string} [endDate] - 结束日期
 * @returns {Promise} Axios Promise
 */
export const getCoachScheduleById = (coachId, startDate, endDate) => {
  return axios.get(`${API_BASE_URL}/api/v1/coaches/schedule/${coachId}`, {
    params: {
      start_date: startDate,
      end_date: endDate
    }
  });
};

/**
 * 删除教练排班
 * @param {number} id - 排班ID
 * @returns {Promise} Axios Promise
 */
export const deleteCoachSchedule = (id) => {
  return axios.delete(`${API_BASE_URL}/api/v1/coaches/schedule/${id}`);
};
/**
 * 批量创建教练排班
 * @param {Array} schedules - 排班数据数组
 * @returns {Promise} Axios Promise
 */
export const batchCreateCoachSchedules = (schedules) => {
  return axios.post(`${API_BASE_URL}/api/v1/coaches/schedule/batch`, { schedules });
};

/**
 * 批量更新教练排班
 * @param {Array} schedules - 排班数据数组
 * @returns {Promise} Axios Promise
 */
export const batchUpdateCoachSchedules = (schedules) => {
  return axios.put(`${API_BASE_URL}/api/v1/coaches/schedule/batch`, { schedules });
};