import { defineStore } from 'pinia';
import { ref } from 'vue';
import * as memberApi from '../api/members.js';

/**
 * 会员状态管理store
 */
export const useMemberStore = defineStore('member', () => {
  // 会员列表
  const members = ref([]);
  
  // 当前编辑的会员
  const currentMember = ref(null);
  
  // 加载状态
  const isLoading = ref(false);
  
  // 错误信息
  const error = ref(null);
  
  /**
   * 获取所有会员
   */
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
  
  /**
   * 获取单个会员详情
   * @param {number} id 会员ID
   */
  const fetchMemberById = async (id) => {
    try {
      isLoading.value = true;
      const response = await memberApi.getMember(id);
      currentMember.value = response.data;
      error.value = null;
    } catch (err) {
      error.value = err.message || '获取会员详情失败';
    } finally {
      isLoading.value = false;
    }
  };
  
  /**
   * 创建新会员
   * @param {object} memberData 会员数据
   */
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
  
  /**
   * 更新会员信息
   * @param {number} id 会员ID
   * @param {object} memberData 更新的会员数据
   */
  const updateMember = async (id, memberData) => {
    try {
      isLoading.value = true;
      const response = await memberApi.updateMember(id, memberData);
      const index = members.value.findIndex(m => m.id === id);
      if (index !== -1) {
        members.value[index] = response.data;
      }
      currentMember.value = response.data;
      error.value = null;
      return response.data;
    } catch (err) {
      error.value = err.message || '更新会员信息失败';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };
  
  /**
   * 删除会员
   * @param {number} id 会员ID
   */
  const deleteMember = async (id) => {
    try {
      isLoading.value = true;
      await memberApi.deleteMember(id);
      members.value = members.value.filter(m => m.id !== id);
      error.value = null;
    } catch (err) {
      error.value = err.message || '删除会员失败';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };
  
  /**
   * 重置当前编辑的会员
   */
  const resetCurrentMember = () => {
    currentMember.value = null;
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
    deleteMember,
    resetCurrentMember
  };
});