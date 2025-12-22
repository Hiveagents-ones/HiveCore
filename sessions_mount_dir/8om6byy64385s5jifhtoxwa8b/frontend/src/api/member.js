import request from '@/utils/request'

// 获取会员列表
export function getMemberList(params) {
  return request({
    url: '/api/v1/members',
    method: 'get',
    params
  })
}

// 获取会员详情
export function getMemberDetail(id) {
  return request({
    url: `/api/v1/members/${id}`,
    method: 'get'
  })
}

// 创建会员
export function createMember(data) {
  return request({
    url: '/api/v1/members',
    method: 'post',
    data
  })
}

// 更新会员信息
export function updateMember(id, data) {
  return request({
    url: `/api/v1/members/${id}`,
    method: 'put',
    data
  })
}

// 删除会员
export function deleteMember(id) {
  return request({
    url: `/api/v1/members/${id}`,
    method: 'delete'
  })
}

// 会员注册
export function registerMember(data) {
  return request({
    url: '/api/v1/members/register',
    method: 'post',
    data
  })
}

// 更新会员等级
export function updateMemberLevel(id, level) {
  return request({
    url: `/api/v1/members/${id}/level`,
    method: 'patch',
    data: { level }
  })
}

// 更新会员课时/有效期
export function updateMemberCredits(id, data) {
  return request({
    url: `/api/v1/members/${id}/credits`,
    method: 'patch',
    data
  })
}
