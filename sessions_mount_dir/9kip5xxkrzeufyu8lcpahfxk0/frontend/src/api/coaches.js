import request from '@/utils/request'

/**
 * 获取教练列表
 * @param {Object} params - 查询参数
 * @returns {Promise}
 */
export function getCoaches(params) {
  return request({
    url: '/api/v1/coaches',
    method: 'get',
    params
  })
}

/**
 * 创建新教练
 * @param {Object} data - 教练数据
 * @returns {Promise}
 */
export function createCoach(data) {
  return request({
    url: '/api/v1/coaches',
    method: 'post',
    data
  })
}

/**
 * 更新教练信息
 * @param {number} id - 教练ID
 * @param {Object} data - 更新数据
 * @returns {Promise}
 */
export function updateCoach(id, data) {
  return request({
    url: `/api/v1/coaches/${id}`,
    method: 'put',
    data
  })
}

/**
 * 删除教练
 * @param {number} id - 教练ID
 * @returns {Promise}
 */
export function deleteCoach(id) {
  return request({
    url: `/api/v1/coaches/${id}`,
    method: 'delete'
  })
}

/**
 * 获取教练排班信息
 * @param {Object} params - 查询参数
 * @returns {Promise}
 */
export function getCoachSchedules(params) {
  return request({
    url: '/api/v1/coaches/schedules',
    method: 'get',
    params
  })
}

/**
 * 创建教练排班
 * @param {Object} data - 排班数据
 * @returns {Promise}
 */
export function createCoachSchedule(data) {
  return request({
    url: '/api/v1/coaches/schedules',
    method: 'post',
    data
  })
}

/**
 * 更新教练排班
 * @param {number} id - 排班ID
 * @param {Object} data - 更新数据
 * @returns {Promise}
 */
export function updateCoachSchedule(id, data) {
  
}

/**
 * 删除教练排班
 * @param {number} id - 排班ID
 * @returns {Promise}
 */
export function deleteCoachSchedule(id) {
  return request({
    url: `/api/v1/coaches/schedules/${id}`,
    method: 'delete'
  })
}

/**
 * 获取教练请假信息
 * @param {Object} params - 查询参数
 * @returns {Promise}
 */
export function getCoachLeaves(params) {
  return request({
    url: '/api/v1/coaches/leaves',
    method: 'get',
    params
  })
}

/**
 * 创建教练请假
 * @param {Object} data - 请假数据
 * @returns {Promise}
 */
export function createCoachLeave(data) {
  return request({
    url: '/api/v1/coaches/leaves',
    method: 'post',
    data
  })
}

/**
 * 更新教练请假
 * @param {number} id - 请假ID
 * @param {Object} data - 更新数据
 * @returns {Promise}
 */
export function updateCoachLeave(id, data) {
  return request({
    url: `/api/v1/coaches/leaves/${id}`,
    method: 'put',
    data
  })
}

/**
 * 删除教练请假
 * @param {number} id - 请假ID
 * @returns {Promise}
 */
export function deleteCoachLeave(id) {
  return request({
    url: `/api/v1/coaches/leaves/${id}`,
    method: 'delete'
  })
  return request({
    url: `/api/v1/coaches/schedules/${id}`,
    method: 'put',
    data
  })
}