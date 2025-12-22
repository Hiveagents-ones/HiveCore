import request from '@/utils/request'

/**
 * 会员签到 API
 * @param {object} data - 签到请求体
 * @param {string} [data.phone] - 会员手机号
 * @param {number} [data.member_id] - 会员ID
 * @param {string} [data.id_card] - 会员身份证号
 * @returns {Promise<object>}
 */
export function checkin(data) {
  return request({
    url: '/api/v1/members/checkin',
    method: 'post',
    data,
  })
}
