import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const memberApi = {
  // 获取会员列表
  getMembers: async (params = {}) => {
    try {
      const response = await apiClient.get('/members', { params });
      return response.data;
    } catch (error) {
      console.error('获取会员列表失败:', error);
      throw error;
    }
  },

  // 获取单个会员详情
  getMember: async (id) => {
    try {
      const response = await apiClient.get(`/members/${id}`);
      return response.data;
    } catch (error) {
      console.error('获取会员详情失败:', error);
      throw error;
    }
  },

  // 创建会员
  createMember: async (memberData) => {
    try {
      const response = await apiClient.post('/members', memberData);
      return response.data;
    } catch (error) {
      console.error('创建会员失败:', error);
      throw error;
    }
  },

  // 更新会员信息
  updateMember: async (id, memberData) => {
    try {
      const response = await apiClient.put(`/members/${id}`, memberData);
      return response.data;
    } catch (error) {
      console.error('更新会员信息失败:', error);
      throw error;
    }
  },

  // 删除会员
  deleteMember: async (id) => {
    try {
      const response = await apiClient.delete(`/members/${id}`);
      return response.data;
    } catch (error) {
      console.error('删除会员失败:', error);
      throw error;
    }
  },

  // 更新会员等级
  updateMemberLevel: async (id, level) => {
    try {
      const response = await apiClient.patch(`/members/${id}/level`, { level });
      return response.data;
    } catch (error) {
      console.error('更新会员等级失败:', error);
      throw error;
    }
  },

  // 更新会员会籍
  updateMembership: async (id, membershipData) => {
    try {
      const response = await apiClient.patch(`/members/${id}/membership`, membershipData);
      return response.data;
    } catch (error) {
      console.error('更新会员会籍失败:', error);
      throw error;
    }
  },
};

export default memberApi;