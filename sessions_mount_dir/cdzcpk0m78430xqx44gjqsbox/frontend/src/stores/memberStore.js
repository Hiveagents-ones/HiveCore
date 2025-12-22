import { defineStore } from 'pinia';
import { ref } from 'vue';
import * as memberApi from '../api/members.js';

/**
 * Pinia store for managing member data
 */
export const useMemberStore = defineStore('member', () => {
  // State
  const members = ref([]);
  const currentMember = ref(null);
  const isLoading = ref(false);
  const error = ref(null);

  // Actions
  const fetchMembers = async () => {
    try {
      isLoading.value = true;
      const response = await memberApi.getMembers();
      members.value = response.data;
      error.value = null;
    } catch (err) {
      error.value = err.message || 'Failed to fetch members';
    } finally {
      isLoading.value = false;
    }
  };

  const fetchMemberById = async (id) => {
    try {
      isLoading.value = true;
      const response = await memberApi.getMemberById(id);
      currentMember.value = response.data;
      error.value = null;
    } catch (err) {
      error.value = err.message || `Failed to fetch member with ID ${id}`;
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
      error.value = err.message || 'Failed to create member';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const updateMember = async (id, memberData) => {
  const deleteMember = async (id) => {
    try {
      isLoading.value = true;
      await memberApi.deleteMember(id);
      members.value = members.value.filter(m => m.id !== id);
      if (currentMember.value && currentMember.value.id === id) {
        currentMember.value = null;
      }
      error.value = null;
    } catch (err) {
      error.value = err.message || `Failed to delete member with ID ${id}`;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };
    try {
      isLoading.value = true;
      const response = await memberApi.updateMember(id, memberData);
      const index = members.value.findIndex(m => m.id === id);
      if (index !== -1) {
        members.value[index] = response.data;
      }
      if (currentMember.value && currentMember.value.id === id) {
        currentMember.value = response.data;
      }
      error.value = null;
      return response.data;
    } catch (err) {
      error.value = err.message || `Failed to update member with ID ${id}`;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const resetCurrentMember = () => {
  
  const getMemberPayments = async (id) => {
    try {
      isLoading.value = true;
      const response = await memberApi.getMemberPayments(id);
      error.value = null;
      return response.data;
    } catch (err) {
      error.value = err.message || `Failed to fetch payments for member with ID ${id}`;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };
    currentMember.value = null;
  };

  return {
    // State
    members,
    currentMember,
    isLoading,
    error,
    
    // Actions
    fetchMembers,
    fetchMemberById,
    createMember,
    updateMember,
    resetCurrentMember,
    deleteMember,
    getMemberPayments
  };
});