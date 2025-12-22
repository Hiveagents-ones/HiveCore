import { defineStore } from 'pinia'
import axios from 'axios'
import { ref, computed } from 'vue'

export const useMemberStore = defineStore('member', () => {
  const members = ref([])
  const currentMember = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const memberCount = computed(() => members.value.length)
  const activeMembers = computed(() => 
    members.value.filter(m => m.status === 'active')
  )

  async function fetchMembers() {
    loading.value = true
    error.value = null
    try {
      const response = await axios.get('/api/v1/members/')
      members.value = response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch members'
      throw error.value
    } finally {
      loading.value = false
    }
  }

  async function createMember(memberData) {
    loading.value = true
    error.value = null
    try {
      const response = await axios.post('/api/v1/members/', memberData)
      members.value.push(response.data)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to create member'
      throw error.value
    } finally {
      loading.value = false
    }
  }

  async function updateMember(memberId, memberData) {
    loading.value = true
    error.value = null
    try {
      const response = await axios.put(`/api/v1/members/${memberId}`, memberData)
      const index = members.value.findIndex(m => m.id === memberId)
      if (index !== -1) {
        members.value[index] = response.data
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to update member'
      throw error.value
    } finally {
      loading.value = false
    }
  }

  async function deleteMember(memberId) {
    loading.value = true
    error.value = null
    try {
      await axios.delete(`/api/v1/members/${memberId}`)
      members.value = members.value.filter(m => m.id !== memberId)
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to delete member'
      throw error.value
    } finally {
      loading.value = false
    }
  }

  async function recordEntry(memberId) {
    loading.value = true
    error.value = null
    try {
      const response = await axios.post(`/api/v1/members/${memberId}/entry`)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to record entry'
      throw error.value
    } finally {
      loading.value = false
    }
  }

  function setCurrentMember(member) {
    currentMember.value = member
  }

  function clearCurrentMember() {
    currentMember.value = null
  }

  return {
    members,
    currentMember,
    loading,
    error,
    memberCount,
    activeMembers,
    fetchMembers,
    createMember,
    updateMember,
    deleteMember,
    recordEntry,
    setCurrentMember,
    clearCurrentMember
  }
})
