import { defineStore } from 'pinia';
import { registerMember, getMembershipTypes } from '../services/api';

export const useRegisterStore = defineStore('register', {
  state: () => ({
    // 表单数据
    formData: {
      name: '',
      phone: '',
      idCard: '',
      membershipType: '',
      privacyAccepted: false
    },
    // 会员卡类型列表
    membershipTypes: [],
    // 加载状态
    loading: false,
    // 错误信息
    error: null,
    // 注册结果
    registrationResult: null
  }),

  getters: {
    // 检查表单是否有效
    isFormValid: (state) => {
      return (
        state.formData.name.trim() !== '' &&
        state.formData.phone.trim() !== '' &&
        state.formData.idCard.trim() !== '' &&
        state.formData.membershipType !== '' &&
        state.formData.privacyAccepted
      );
    },
    // 获取选中的会员卡类型信息
    selectedMembershipType: (state) => {
      return state.membershipTypes.find(
        (type) => type.id === state.formData.membershipType
      );
    }
  },

  actions: {
    // 重置表单
    resetForm() {
      this.formData = {
        name: '',
        phone: '',
        idCard: '',
        membershipType: '',
        privacyAccepted: false
      };
      this.error = null;
      this.registrationResult = null;
    },

    // 更新表单字段
    updateFormField(field, value) {
      this.formData[field] = value;
      // 清除之前的错误信息
      if (this.error) {
        this.error = null;
      }
    },

    // 获取会员卡类型列表
    async fetchMembershipTypes() {
      try {
        this.loading = true;
        const response = await getMembershipTypes();
        this.membershipTypes = response.data || [];
      } catch (error) {
        this.error = error.message || '获取会员卡类型失败';
        console.error('Failed to fetch membership types:', error);
      } finally {
        this.loading = false;
      }
    },

    // 提交注册
    async submitRegistration() {
      // 验证表单
      if (!this.isFormValid) {
        this.error = '请填写所有必填字段并同意隐私政策';
        return;
      }

      try {
        this.loading = true;
        this.error = null;
        
        // 准备提交数据
        const submitData = {
          name: this.formData.name.trim(),
          phone: this.formData.phone.trim(),
          id_card: this.formData.idCard.trim(),
          membership_type_id: this.formData.membershipType
        };

        // 调用注册API
        const response = await registerMember(submitData);
        this.registrationResult = response;
        
        // 注册成功后重置表单
        this.resetForm();
        
        return response;
      } catch (error) {
        // 处理不同类型的错误
        if (error.message.includes('手机号')) {
          this.error = '手机号格式不正确或已被注册';
        } else if (error.message.includes('身份证')) {
          this.error = '身份证号格式不正确或已被使用';
        } else if (error.message.includes('会员卡类型')) {
          this.error = '所选会员卡类型无效';
        } else {
          this.error = error.message || '注册失败，请稍后重试';
        }
        console.error('Registration failed:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    // 初始化
    async initialize() {
      await this.fetchMembershipTypes();
    }
  }
});