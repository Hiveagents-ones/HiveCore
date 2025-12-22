import { defineStore } from 'pinia';
import memberApi from '../api/member.js';

/**
 * 会员状态管理store
 */
export const useMemberStore = defineStore('member', {
  state: () => ({
    members: [],
    currentMember: null,
    loading: false,
    error: null
  }),

  actions: {
    /**
     * 获取所有会员
     */
    async fetchMembers() {
      this.loading = true;
      try {
        const response = await memberApi.getMembers();
        this.members = response.data;
        this.error = null;
      } catch (err) {
        this.error = err.response?.data?.message || err.message;
      } finally {
        this.loading = false;
      }
    },

    /**
     * 获取单个会员详情
     * @param {number} memberId 会员ID
     */
    async fetchMember(memberId) {
      this.loading = true;
      try {
        const response = await memberApi.getMember(memberId);
        this.currentMember = response.data;
        this.error = null;
      } catch (err) {
        this.error = err.response?.data?.message || err.message;
      } finally {
        this.loading = false;
      }
    },

    /**
     * 创建新会员
     * @param {Object} memberData 会员数据
     */
    async createMember(memberData) {
      this.loading = true;
      try {
        const response = await memberApi.createMember(memberData);
        this.members.push(response.data);
        this.error = null;
        return response.data;
      } catch (err) {
        this.error = err.response?.data?.message || err.message;
        throw err;
      } finally {
        this.loading = false;
      }
    },

    /**
     * 更新会员信息
     * @param {number} memberId 会员ID
     * @param {Object} memberData 更新的会员数据
     */
    async updateMember(memberId, memberData) {
      this.loading = true;
      try {
        const response = await memberApi.updateMember(memberId, memberData);
        const index = this.members.findIndex(m => m.id === memberId);
        if (index !== -1) {
          this.members.splice(index, 1, response.data);
        }
        if (this.currentMember?.id === memberId) {
          this.currentMember = response.data;
        }
        this.error = null;
        return response.data;
      } catch (err) {
        this.error = err.response?.data?.message || err.message;
        throw err;
      } finally {
        this.loading = false;
      }
    },

    /**
     * 删除会员
     * @param {number} memberId 会员ID
     */
    async deleteMember(memberId) {
      this.loading = true;
      try {
        await memberApi.deleteMember(memberId);
        this.members = this.members.filter(m => m.id !== memberId);
        if (this.currentMember?.id === memberId) {
          this.currentMember = null;
        }
        this.error = null;
      } catch (err) {
        this.error = err.response?.data?.message || err.message;
        throw err;
      } finally {
        this.loading = false;
      }
    },

    /**
     * 重置当前选中的会员
     */
    resetCurrentMember() {
      this.currentMember = null;
    }
  },

  getters: {
    /**
     * 获取会员总数
     */
    totalMembers: (state) => state.members.length,
    
    /**
     * 根据ID获取会员
     */
    getMemberById: (state) => (id) => {
      return state.members.find(member => member.id === id);
    }
  }
});