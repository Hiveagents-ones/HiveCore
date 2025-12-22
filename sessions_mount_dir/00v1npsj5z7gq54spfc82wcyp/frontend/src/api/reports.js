import request from '@/utils/request';

/**
 * 获取财务报表
 * @param {Object} params - 查询参数
 * @param {string} params.startDate - 开始日期
 * @param {string} params.endDate - 结束日期
 * @param {string} [params.type] - 报表类型
 * @returns {Promise} 包含报表数据的Promise
 */
export function getFinancialReports(params) {
  return request({
    url: '/api/v1/reports',
    method: 'get',
    params
  });
}

/**
 * 获取会员费统计报表
 * @param {Object} params - 查询参数
 * @param {string} params.year - 年份
 * @param {string} [params.month] - 月份
 * @returns {Promise} 包含会员费统计数据的Promise
 */
export function getMembershipFeeReports(params) {
  return request({
    url: '/api/v1/reports/membership-fee',
    method: 'get',
    params
  });
}

/**
 * 获取课程收入报表
 * @param {Object} params - 查询参数
 * @param {string} params.startDate - 开始日期
 * @param {string} params.endDate - 结束日期
 * @returns {Promise} 包含课程收入数据的Promise
 */
export function getCourseIncomeReports(params) {
  return request({
    url: '/api/v1/reports/course-income',
    method: 'get',
    params
  });
}

/**
 * 导出报表数据
 * @param {Object} params - 查询参数
 * @param {string} params.type - 报表类型
 * @param {string} params.format - 导出格式 (csv/excel)
 * @returns {Promise} 包含导出文件的Promise
 */
export function exportReports(params) {
  return request({
    url: '/api/v1/reports/export',
    method: 'get',
    params,
    responseType: 'blob'
  });
}