import { defineStore } from 'pinia';
import { ref } from 'vue';
import * as memberApi from '../api/members.js';

/**
 * 会员状态管理(Pinia store)
 * 管理会员信息的录入、查看和修改功能
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
      const response = await memberApi.getMembers();
      members.value = response.data;
      error.value = null;
    } catch (err) {
      error.value = err.message || '获取会员列表失败';
    } finally {
      isLoading.value = false;
    }
  };

  const fetchMemberById = async (id) => {
    try {
      isLoading.value = true;
      const response = await memberApi.getMember(id);
      currentMember.value = response.data;
      error.value = null;
    } catch (err) {
      error.value = err.message || '获取会员信息失败';
    } finally {
      isLoading.value = false;
    }
  };

  const createMember = async (memberData) => {
    try {
      isLoading.value = true;
      const response = await memberApi.createMember(memberData);
      members.value.push(response.data);
      error.value = null;
      return response.data;
    } catch (err) {
      error.value = err.message || '创建会员失败';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const updateMember = async (id, memberData) => {
    try {
      isLoading.value = true;
      const response = await memberApi.updateMember(id, memberData);
      const index = members.value.findIndex(m => m.id === id);
      if (index !== -1) {
        members.value[index] = response.data;
      }
      if (currentMember.value?.id === id) {
        currentMember.value = response.data;
      }
      error.value = null;
      return response.data;
    } catch (err) {
      error.value = err.message || '更新会员失败';
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
    resetCurrentMember
  };
});