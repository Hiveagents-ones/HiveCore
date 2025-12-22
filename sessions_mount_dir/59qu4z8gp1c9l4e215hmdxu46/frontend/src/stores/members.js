import { defineStore } from 'pinia';
import {
  getMembers,
  createMember,
  updateMember,
  deleteMember,
  getMemberCards,
  updateMemberCard
} from '@/api/members';

export const useMemberStore = defineStore('members', {
  state: () => ({
    members: [],
    currentMember: null,
    memberCards: [],
    loading: false,
    error: null
  }),

  actions: {
    /**
     * 获取会员列表
     * @param {Object} params - 查询参数
     */
    async fetchMembers(params = {}) {
      this.loading = true;
      try {
        const response = await getMembers(params);
        this.members = response.data;
        this.error = null;
      } catch (error) {
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },

    /**
     * 创建新会员
     * @param {Object} memberData - 会员数据
     */
    async addMember(memberData) {
      this.loading = true;
      try {
        const response = await createMember(memberData);
        this.members.push(response.data);
        this.error = null;
        return response.data;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    /**
     * 更新会员信息
     * @param {Number} memberId - 会员ID
     * @param {Object} memberData - 更新的会员数据
     */
    async modifyMember(memberId, memberData) {
      this.loading = true;
      try {
        const response = await updateMember(memberId, memberData);
        const index = this.members.findIndex(m => m.id === memberId);
        if (index !== -1) {
          this.members[index] = response.data;
        }
        this.error = null;
        return response.data;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    /**
     * 删除会员
     * @param {Number} memberId - 会员ID
     */
    async removeMember(memberId) {
      this.loading = true;
      try {
        await deleteMember(memberId);
        this.members = this.members.filter(m => m.id !== memberId);
        this.error = null;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    /**
     * 获取会员卡信息
     * @param {Number} memberId - 会员ID
     */
    async fetchMemberCards(memberId) {
      this.loading = true;
      try {
        const response = await getMemberCards(memberId);
        this.memberCards = response.data;
        this.error = null;
      } catch (error) {
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },

    /**
     * 更新会员卡信息
     * @param {Number} memberId - 会员ID
     * @param {Number} cardId - 会员卡ID
     * @param {Object} cardData - 更新的会员卡数据
     */
    async modifyMemberCard(memberId, cardId, cardData) {
      this.loading = true;
      try {
        const response = await updateMemberCard(memberId, cardId, cardData);
        const index = this.memberCards.findIndex(c => c.id === cardId);
        if (index !== -1) {
          this.memberCards[index] = response.data;
        }
        this.error = null;
        return response.data;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    /**
     * 设置当前选中的会员
     * @param {Object|null} member - 会员对象或null
     */
    setCurrentMember(member) {
      this.currentMember = member;
    },

    /**
     * 重置会员卡列表
     */
    resetMemberCards() {
      this.memberCards = [];
    }
  },

  getters: {
    /**
     * 获取所有会员
     * @returns {Array} - 会员列表
     */
    allMembers: (state) => state.members,

    /**
     * 获取当前选中的会员
     * @returns {Object|null} - 当前会员或null
     */
    selectedMember: (state) => state.currentMember,

    /**
     * 获取会员卡列表
     * @returns {Array} - 会员卡列表
     */
    allMemberCards: (state) => state.memberCards,

    /**
     * 获取加载状态
     * @returns {Boolean} - 是否正在加载
     */
    isLoading: (state) => state.loading,

    /**
     * 获取错误信息
     * @returns {String|null} - 错误信息或null
     */
    getError: (state) => state.error
  }
});
