import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from 'axios';

// API基础URL，根据环境变量或配置文件设置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const useMembersStore = defineStore('members', () => {
  // 状态
  const members = ref([]);
  const currentMember = ref(null);
  const loading = ref(false);
  const error = ref(null);
  const pagination = ref({
    page: 1,
    size: 10,
    total: 0
  });

  // 计算属性
  const memberCount = computed(() => members.value.length);
  const activeMembers = computed(() => members.value.filter(member => {
    const today = new Date();
    const expiryDate = new Date(member.expiry_date);
    return expiryDate >= today;
  }));
  const expiredMembers = computed(() => members.value.filter(member => {
    const today = new Date();
    const expiryDate = new Date(member.expiry_date);
    return expiryDate < today;
  }));

  // 方法
  const fetchMembers = async (params = {}) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await axios.get(`${API_BASE_URL}/members`, {
        params: {
          skip: (pagination.value.page - 1) * pagination.value.size,
          limit: pagination.value.size,
          ...params
        }
      });
      members.value = response.data.items || [];
      pagination.value.total = response.data.total || 0;
    } catch (err) {
      error.value = err.response?.data?.detail || '获取会员列表失败';
      console.error('Error fetching members:', err);
    } finally {
      loading.value = false;
    }
  };

  const fetchMemberById = async (id) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await axios.get(`${API_BASE_URL}/members/${id}`);
      currentMember.value = response.data;
      return response.data;
    } catch (err) {
      error.value = err.response?.data?.detail || '获取会员详情失败';
      console.error('Error fetching member:', err);
      return null;
    } finally {
      loading.value = false;
    }
  };

  const createMember = async (memberData) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await axios.post(`${API_BASE_URL}/members`, memberData);
      members.value.push(response.data);
      return response.data;
    } catch (err) {
      error.value = err.response?.data?.detail || '创建会员失败';
      console.error('Error creating member:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const updateMember = async (id, memberData) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await axios.put(`${API_BASE_URL}/members/${id}`, memberData);
      const index = members.value.findIndex(member => member.id === id);
      if (index !== -1) {
        members.value[index] = response.data;
      }
      if (currentMember.value && currentMember.value.id === id) {
        currentMember.value = response.data;
      }
      return response.data;
    } catch (err) {
      error.value = err.response?.data?.detail || '更新会员失败';
      console.error('Error updating member:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const deleteMember = async (id) => {
    loading.value = true;
    error.value = null;
    try {
      await axios.delete(`${API_BASE_URL}/members/${id}`);
      members.value = members.value.filter(member => member.id !== id);
      if (currentMember.value && currentMember.value.id === id) {
        currentMember.value = null;
      }
      return true;
    } catch (err) {
      error.value = err.response?.data?.detail || '删除会员失败';
      console.error('Error deleting member:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const searchMembers = async (query) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await axios.get(`${API_BASE_URL}/members/search`, {
        params: { q: query }
      });
      members.value = response.data || [];
      return response.data;
    } catch (err) {
      error.value = err.response?.data?.detail || '搜索会员失败';
      console.error('Error searching members:', err);
      return [];
    } finally {
      loading.value = false;
    }
  };

  const setPagination = (page, size) => {
    pagination.value.page = page;
    pagination.value.size = size;
  };

  const clearError = () => {
    error.value = null;
  };

  const resetState = () => {
    members.value = [];
    currentMember.value = null;
    loading.value = false;
    error.value = null;
    pagination.value = {
      page: 1,
      size: 10,
      total: 0
    };
  };

  return {
    // 状态
    members,
    currentMember,
    loading,
    error,
    pagination,
    
    // 计算属性
    memberCount,
    activeMembers,
    expiredMembers,
    
    // 方法
    fetchMembers,
    fetchMemberById,
    createMember,
    updateMember,
    deleteMember,
    searchMembers,
    setPagination,
    clearError,
    resetState
  };
});