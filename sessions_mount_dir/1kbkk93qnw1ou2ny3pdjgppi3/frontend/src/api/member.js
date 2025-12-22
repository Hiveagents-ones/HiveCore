import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000', // 假设后端服务运行在8000端口，可根据实际环境调整
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 会员注册
 * @param {object} memberData - 会员数据 { name, phone, id_card }
 * @returns {Promise<object>} - 注册成功的会员信息
 */
export const registerMember = async (memberData) => {
  try {
    const response = await apiClient.post('/api/v1/members', memberData);
    return response.data;
  } catch (error) {
    // 抛出包含详细信息的错误，供上层处理
    if (error.response) {
      // 服务器响应了状态码，但不在 2xx 范围内
      console.error('API Error Data:', error.response.data);
      console.error('API Error Status:', error.response.status);
      // 优先使用后端返回的 detail 信息
      throw new Error(error.response.data.detail || '注册失败，请稍后再试');
    } else if (error.request) {
      // 请求已发出，但没有收到响应
      console.error('API No Response:', error.request);
      throw new Error('服务器无响应，请检查网络连接');
    } else {
      // 在设置请求时触发了错误
      console.error('API Request Setup Error:', error.message);
      throw new Error('请求配置错误');
    }
  }
};