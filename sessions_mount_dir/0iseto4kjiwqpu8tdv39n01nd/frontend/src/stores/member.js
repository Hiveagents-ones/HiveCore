import { defineStore } from 'pinia';
import axios from 'axios';

export const useMemberStore = defineStore('member', {
  state: () => ({
    members: [],
    currentMember: null,
    loading: false,
    error: null,
  }),
  getters: {
    getMemberById: (state) => (id) => {
      return state.members.find(member => member.id === id);
    },
    getMembersByLevel: (state) => (level) => {
      return state.members.filter(member => member.level === level);
    },
  },
  actions: {
    async fetchMembers() {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get('/api/members');
        this.members = response.data;
      } catch (error) {
        this.error = error.message || 'Failed to fetch members';
        console.error('Error fetching members:', error);
      } finally {
        this.loading = false;
      }
    },
    async fetchMember(id) {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get(`/api/members/${id}`);
        this.currentMember = response.data;
      } catch (error) {
        this.error = error.message || 'Failed to fetch member';
        console.error('Error fetching member:', error);
      } finally {
        this.loading = false;
      }
    },
    async createMember(memberData) {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.post('/api/members', memberData);
        this.members.push(response.data);
        return response.data;
      } catch (error) {
        this.error = error.message || 'Failed to create member';
        console.error('Error creating member:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },
    async updateMember(id, memberData) {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.put(`/api/members/${id}`, memberData);
        const index = this.members.findIndex(member => member.id === id);
        if (index !== -1) {
          this.members[index] = response.data;
        }
        if (this.currentMember && this.currentMember.id === id) {
          this.currentMember = response.data;
        }
        return response.data;
      } catch (error) {
        this.error = error.message || 'Failed to update member';
        console.error('Error updating member:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },
    async deleteMember(id) {
      this.loading = true;
      this.error = null;
      try {
        await axios.delete(`/api/members/${id}`);
        this.members = this.members.filter(member => member.id !== id);
        if (this.currentMember && this.currentMember.id === id) {
          this.currentMember = null;
        }
      } catch (error) {
        this.error = error.message || 'Failed to delete member';
        console.error('Error deleting member:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },
    clearError() {
      this.error = null;
    },
  },
});
