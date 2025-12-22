import { defineStore } from 'pinia';
import { registerMember } from '@/api/member';

export const useMemberStore = defineStore('member', {
  state: () => ({
    // 注册状态
    registrationStatus: 'idle', // 'idle' | 'registering' | 'success' | 'error'
    registeredMemberInfo: null, // 存储注册成功后的会员信息
    errorMessage: null, // 存储错误信息
  }),
  actions: {
    /**
     * 执行会员注册操作
     * @param {object} payload - { name, phone, id_card }
     */
    async register(payload) {
      this.registrationStatus = 'registering';
      this.errorMessage = null;
      this.registeredMemberInfo = null;
      try {
        const response = await registerMember(payload);
        this.registrationStatus = 'success';
        // 假设后端返回完整的会员对象，符合 Member 模型
        this.registeredMemberInfo = response;
      } catch (error) {
        this.registrationStatus = 'error';
        // 捕获 API 层抛出的、已处理过的错误信息
        this.errorMessage = error.message;
      }
    },

    /**
     * 重置 Store 状态
     */
    resetState() {
      this.registrationStatus = 'idle';
      this.registeredMemberInfo = null;
      this.errorMessage = null;
    }
  },
  getters: {
    isLoading: (state) => state.registrationStatus === 'registering',
    isSuccess: (state) => state.registrationStatus === 'success',
    isError: (state) => state.registrationStatus === 'error',
  }
});
