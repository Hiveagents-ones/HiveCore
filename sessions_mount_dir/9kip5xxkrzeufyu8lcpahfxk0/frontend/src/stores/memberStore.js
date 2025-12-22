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

  // Getters
  const getMemberById = (id) => {
    return members.value.find(member => member.id === id);
  };

  // Actions
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

  const fetchMemberById = async (id) => {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await memberApi.getMember(id);
      currentMember.value = response.data;
    } catch (err) {
      error.value = err.message || 'Failed to fetch member details';
      console.error('Error fetching member:', err);
    } finally {
      isLoading.value = false;
    }
  };

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

  const updateMember = async (id, memberData) => {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await memberApi.updateMember(id, memberData);
      const index = members.value.findIndex(m => m.id === id);
      if (index !== -1) {
        members.value[index] = response.data;
      }
      if (currentMember.value?.id === id) {
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

  const deleteMember = async (id) => {
    isLoading.value = true;
    error.value = null;
    try {
      await memberApi.deleteMember(id);
      members.value = members.value.filter(member => member.id !== id);
      if (currentMember.value?.id === id) {
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
    // State
    members,
    currentMember,
    isLoading,
    error,
    
    // Getters
    getMemberById,
    
    // Actions
    fetchMembers,
    fetchMemberById,
    createMember,
    updateMember,
    deleteMember
  };
});