import { defineStore } from 'pinia';
import {
  getMembers,
  getMemberById,
  createMember,
  updateMember,
  deleteMember
} from '../api/members';

export const useMemberStore = defineStore('member', {
  state: () => ({
    members: [],
    currentMember: null,
    loading: false,
    error: null
  }),

  actions: {
    /**
     * 更新会员信息
     * @param {number} id 会员ID
     * @param {Object} memberData 更新的会员数据
     */
    async updateMember(id, memberData) {
      this.loading = true;
      try {
        const updatedMember = await updateMember(id, memberData);
        const index = this.members.findIndex(m => m.id === id);
        if (index !== -1) {
          this.members.splice(index, 1, updatedMember);
        }
        if (this.currentMember && this.currentMember.id === id) {
          this.currentMember = updatedMember;
        }
        this.error = null;
        return updatedMember;
      } catch (error) {
        this.error = error;
        throw error;
      } finally {
        this.loading = false;
      }
    },
    /**
     * 更新会员信息
     * @param {number} id 会员ID
     * @param {Object} memberData 更新的会员数据
     */
    async updateMember(id, memberData) {
     * 获取所有会员
     */
    async fetchMembers() {
      this.loading = true;
      try {
        this.members = await getMembers();
        this.error = null;
      } catch (error) {
        this.error = error;
      } finally {
        this.loading = false;
      }
    },

    /**
     * 获取单个会员详情
     * @param {number} id 会员ID
     */
    async fetchMemberById(id) {
      this.loading = true;
      try {
        this.currentMember = await getMemberById(id);
        this.error = null;
      } catch (error) {
        this.error = error;
      } finally {
        this.loading = false;
      }
    },

    /**
     * 创建新会员
     * @param {Object} memberData 会员数据
     */
    async addMember(memberData) {
      this.loading = true;
      try {
        const newMember = await createMember(memberData);
        this.members.push(newMember);
        this.error = null;
        return newMember;
      } catch (error) {
        this.error = error;
        throw error;
      } finally {
        this.loading = false;
      }
    },


  

    /**
     * 删除会员
     * @param {number} id 会员ID
     */
    async removeMember(id) {
      this.loading = true;
      try {
        await deleteMember(id);
        const index = this.members.findIndex(m => m.id === id);
        if (index !== -1) {
          this.members.splice(index, 1);
        }
        if (this.currentMember && this.currentMember.id === id) {
          this.currentMember = null;
        }
        this.error = null;
      } catch (error) {
        this.error = error;
        throw error;
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
     * 获取所有会员
     */
    allMembers: (state) => state.members,
    
    /**
     * 获取当前选中的会员
     */
    selectedMember: (state) => state.currentMember,
    
    /**
     * 检查是否正在加载
     */
    isLoading: (state) => state.loading,
    
    /**
     * 获取错误信息
     */
    getError: (state) => state.error
  }
});