import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from 'axios';

export const useMemberStore = defineStore('member', () => {
  // State
  const members = ref([]);
  const currentMember = ref(null);
  const loading = ref(false);
  const error = ref(null);

  // Getters
  const activeMembers = computed(() => 
    members.value.filter(member => member.status === 'active')
  );

  const memberById = computed(() => {
    return (id) => members.value.find(member => member.id === id);
  });

  // Actions
  const fetchMembers = async () => {
    loading.value = true;
    error.value = null;
    try {
      const response = await axios.get('/api/v1/members');
      members.value = response.data;
    } catch (err) {
      error.value = err.message || 'Failed to fetch members';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const fetchMember = async (id) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await axios.get(`/api/v1/members/${id}`);
      currentMember.value = response.data;
      return response.data;
    } catch (err) {
      error.value = err.message || 'Failed to fetch member';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const createMember = async (memberData) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await axios.post('/api/v1/members', memberData);
      members.value.push(response.data);
      return response.data;
    } catch (err) {
      error.value = err.message || 'Failed to create member';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const updateMember = async (id, memberData) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await axios.put(`/api/v1/members/${id}`, memberData);
      const index = members.value.findIndex(member => member.id === id);
      if (index !== -1) {
        members.value[index] = response.data;
      }
      if (currentMember.value?.id === id) {
        currentMember.value = response.data;
      }
      return response.data;
    } catch (err) {
      error.value = err.message || 'Failed to update member';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const deleteMember = async (id) => {
    loading.value = true;
    error.value = null;
    try {
      await axios.delete(`/api/v1/members/${id}`);
      members.value = members.value.filter(member => member.id !== id);
      if (currentMember.value?.id === id) {
        currentMember.value = null;
      }
    } catch (err) {
      error.value = err.message || 'Failed to delete member';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const setCurrentMember = (member) => {
    currentMember.value = member;
  };

  const clearCurrentMember = () => {
    currentMember.value = null;
  };

  const clearError = () => {
    error.value = null;
  };

  return {
    // State
    members,
    currentMember,
    loading,
    error,
    
    // Getters
    activeMembers,
    memberById,
    
    // Actions
    fetchMembers,
    fetchMember,
    createMember,
    updateMember,
    deleteMember,
    setCurrentMember,
    clearCurrentMember,
    clearError
  };
});