import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { memberApi } from '../api/member';

export const useMemberStore = defineStore('member', () => {
  // State
  const members = ref([]);
  const currentMember = ref(null);
  const loading = ref(false);
  const error = ref(null);
  const pagination = ref({
    page: 1,
    pageSize: 10,
    total: 0
  });

  // Getters
  const activeMembers = computed(() => 
    members.value.filter(member => member.status === 'active')
  );

  const expiredMembers = computed(() => 
    members.value.filter(member => member.status === 'expired')
  );

  const frozenMembers = computed(() => 
    members.value.filter(member => member.status === 'frozen')
  );

  const memberStats = computed(() => ({
    total: members.value.length,
    active: activeMembers.value.length,
    expired: expiredMembers.value.length,
    frozen: frozenMembers.value.length
  }));

  // Actions
  const fetchMembers = async (params = {}) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await memberApi.getMembers({
        page: pagination.value.page,
        pageSize: pagination.value.pageSize,
        ...params
      });
      members.value = response.data.items;
      pagination.value = {
        page: response.data.page,
        pageSize: response.data.pageSize,
        total: response.data.total
      };
    } catch (err) {
      error.value = err.message || 'Failed to fetch members';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const fetchMemberById = async (id) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await memberApi.getMemberById(id);
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
      const response = await memberApi.createMember(memberData);
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
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const deleteMember = async (id) => {
    loading.value = true;
    error.value = null;
    try {
      await memberApi.deleteMember(id);
      members.value = members.value.filter(m => m.id !== id);
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

  const renewMembership = async (id, renewalData) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await memberApi.renewMembership(id, renewalData);
      const index = members.value.findIndex(m => m.id === id);
      if (index !== -1) {
        members.value[index] = response.data;
      }
      if (currentMember.value?.id === id) {
        currentMember.value = response.data;
      }
      return response.data;
    } catch (err) {
      error.value = err.message || 'Failed to renew membership';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const batchImportMembers = async (file) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await memberApi.batchImportMembers(file);
      await fetchMembers();
      return response.data;
    } catch (err) {
      error.value = err.message || 'Failed to import members';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const exportMembers = async (params = {}) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await memberApi.exportMembers(params);
      return response.data;
    } catch (err) {
      error.value = err.message || 'Failed to export members';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const searchMembers = async (query) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await memberApi.searchMembers(query);
      return response.data;
    } catch (err) {
      error.value = err.message || 'Failed to search members';
      throw err;
    } finally {
      loading.value = false;
    }
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
      pageSize: 10,
      total: 0
    };
  };

  return {
    // State
    members,
    currentMember,
    loading,
    error,
    pagination,
    
    // Getters
    activeMembers,
    expiredMembers,
    frozenMembers,
    memberStats,
    
    // Actions
    fetchMembers,
    fetchMemberById,
    createMember,
    updateMember,
    deleteMember,
    renewMembership,
    batchImportMembers,
    exportMembers,
    searchMembers,
    clearError,
    resetState
  };
});