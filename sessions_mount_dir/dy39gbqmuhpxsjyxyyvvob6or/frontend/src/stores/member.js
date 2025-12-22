import { defineStore } from 'pinia';
import { ref } from 'vue';
import * as memberApi from '../api/members.js';

/**
 * 会员状态管理(Pinia store)
 * 管理会员信息，包括注册、查询、修改和删除会员资料
 */
export const useMemberStore = defineStore('member', () => {
  // 状态
  const members = ref([]);
  const currentMember = ref(null);
  const isLoading = ref(false);
  const error = ref(null);

  // 操作
  const fetchMembers = async () => {
    try {
      isLoading.value = true;
      error.value = null;
      const response = await memberApi.getMembers();
      members.value = response.data;
    } catch (err) {
      error.value = err.message || '获取会员列表失败';
      console.error('获取会员列表失败:', err);
    } finally {
      isLoading.value = false;
    }
  };

  const fetchMemberById = async (id) => {
    try {
      isLoading.value = true;
      error.value = null;
      const response = await memberApi.getMember(id);
      currentMember.value = response.data;
    } catch (err) {
      error.value = err.message || '获取会员详情失败';
      console.error('获取会员详情失败:', err);
    } finally {
      isLoading.value = false;
    }
  };

  const createMember = async (memberData) => {
    try {
      isLoading.value = true;
      error.value = null;
      const response = await memberApi.createMember(memberData);
      members.value.push(response.data);
      return response.data;
    } catch (err) {
      error.value = err.message || '创建会员失败';
      console.error('创建会员失败:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const updateMember = async (id, memberData) => {
    try {
      isLoading.value = true;
      error.value = null;
      const response = await memberApi.updateMember(id, memberData);
      const index = members.value.findIndex(m => m.id === id);
      if (index !== -1) {
        members.value[index] = response.data;
      }
      if (currentMember.value && currentMember.value.id === id) {
        currentMember.value = response.data;
      }
      return response.data;
    } catch (err) {
      error.value = err.message || '更新会员失败';
      console.error('更新会员失败:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const deleteMember = async (id) => {
    try {
      isLoading.value = true;
      error.value = null;
      await memberApi.deleteMember(id);
      members.value = members.value.filter(m => m.id !== id);
      if (currentMember.value && currentMember.value.id === id) {
        currentMember.value = null;
      }
    } catch (err) {
      error.value = err.message || '删除会员失败';
      console.error('删除会员失败:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  // 重置当前选中的会员
  const resetCurrentMember = () => {
    currentMember.value = null;
  };

  return {
    // 状态
    members,
    currentMember,
    isLoading,
    error,
    
    // 操作
    fetchMembers,
    fetchMemberById,
    createMember,
    updateMember,
    deleteMember,
    resetCurrentMember
  };
});