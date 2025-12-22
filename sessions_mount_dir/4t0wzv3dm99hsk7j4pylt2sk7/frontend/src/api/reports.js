import request from '@/utils/request'

export function getMemberTrend(params) {
  return request({
    url: '/api/v1/reports/member-trend',
    method: 'get',
    params
  })
}

export function getCoursePopularity(params) {
  return request({
    url: '/api/v1/reports/course-popularity',
    method: 'get',
    params
  })
}

export function getRevenueStats(params) {
  return request({
    url: '/api/v1/reports/revenue-stats',
    method: 'get',
    params
  })
}