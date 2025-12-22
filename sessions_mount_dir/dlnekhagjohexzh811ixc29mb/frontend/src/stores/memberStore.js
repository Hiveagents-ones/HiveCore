import { defineStore } from 'pinia';
import { ref } from 'vue';
import * as memberApi from '../api/members.js';

export const useMemberStore = defineStore('member', () => {
  const members = ref([]);
  const currentMember = ref(null);
  const isLoading = ref(false);
  const error = ref(null);

  // 获取所有会员
  const fetchMembers = async () => {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await memberApi.getMembers();
      members.value = response.data;
    } catch (err) {
      error.value = err.message || 'Failed to fetch members';
      console.error('Error fetching members:', err);
    } finally {
      isLoading.value = false;
    }
  };

  // 获取单个会员详情
  const fetchMemberById = async (id) => {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await memberApi.getMemberById(id);
      currentMember.value = response.data;
    } catch (err) {
      error.value = err.message || 'Failed to fetch member details';
      console.error('Error fetching member:', err);
    } finally {
      isLoading.value = false;
    }
  };

  // 创建新会员
  const createMember = async (memberData) => {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await memberApi.createMember(memberData);
      members.value.push(response.data);
      return response.data;
    } catch (err) {
      error.value = err.message || 'Failed to create member';
      console.error('Error creating member:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  // 更新会员信息
  const updateMember = async (id, memberData) => {
    isLoading.value = true;
    error.value = null;
    try {
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
      error.value = err.message || 'Failed to update member';
      console.error('Error updating member:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  // 删除会员
  const deleteMember = async (id) => {
    isLoading.value = true;
    error.value = null;
    try {
      await memberApi.deleteMember(id);
      members.value = members.value.filter(m => m.id !== id);
      if (currentMember.value && currentMember.value.id === id) {
        currentMember.value = null;
      }
    } catch (err) {
      error.value = err.message || 'Failed to delete member';
      console.error('Error deleting member:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  return {
    members,
    currentMember,
    isLoading,
    error,
    fetchMembers,
    fetchMemberById,
    createMember,
    updateMember,
    deleteMember
  };
});