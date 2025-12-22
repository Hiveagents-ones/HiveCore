import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { registerUser } from '../services/api.js';
import { useI18n } from 'vue-i18n';

export const useRegisterStore = defineStore('register', () => {
  const { t } = useI18n();
  
  // 表单数据
  const form = ref({
    name: '',
    phone: '',
    idCard: '',
    password: '',
    confirmPassword: ''
  });
  
  // 表单验证错误
  const errors = ref({});
  
  // 加载状态
  const isLoading = ref(false);
  
  // 注册结果
  const registrationResult = ref(null);
  
  // 计算属性：表单是否有效
  const isFormValid = computed(() => {
    return Object.keys(errors.value).length === 0 && 
           form.value.name && 
           form.value.phone && 
           form.value.idCard && 
           form.value.password && 
           form.value.confirmPassword;
  });
  
  // 验证函数
  const validateForm = () => {
    errors.value = {};
    
    // 姓名验证
    if (!form.value.name) {
      errors.value.name = t('register.errors.nameRequired');
    } else if (form.value.name.length < 2) {
      errors.value.name = t('register.errors.nameTooShort');
    }
    
    // 手机号验证
    const phoneRegex = /^1[3-9]\d{9}$/;
    if (!form.value.phone) {
      errors.value.phone = t('register.errors.phoneRequired');
    } else if (!phoneRegex.test(form.value.phone)) {
      errors.value.phone = t('register.errors.phoneInvalid');
    }
    
    // 身份证号验证
    const idCardRegex = /(^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$)/;
    if (!form.value.idCard) {
      errors.value.idCard = t('register.errors.idCardRequired');
    } else if (!idCardRegex.test(form.value.idCard)) {
      errors.value.idCard = t('register.errors.idCardInvalid');
    }
    
    // 密码验证
    if (!form.value.password) {
      errors.value.password = t('register.errors.passwordRequired');
    } else if (form.value.password.length < 6) {
      errors.value.password = t('register.errors.passwordTooShort');
    }
    
    // 确认密码验证
    if (!form.value.confirmPassword) {
      errors.value.confirmPassword = t('register.errors.confirmPasswordRequired');
    } else if (form.value.password !== form.value.confirmPassword) {
      errors.value.confirmPassword = t('register.errors.passwordMismatch');
    }
    
    return Object.keys(errors.value).length === 0;
  };
  
  // 注册函数
  const register = async () => {
    if (!validateForm()) {
      return false;
    }
    
    isLoading.value = true;
    registrationResult.value = null;
    
    try {
      const userData = {
        name: form.value.name,
        phone: form.value.phone,
        id_card: form.value.idCard,
        password: form.value.password
      };
      
      const response = await registerUser(userData);
      registrationResult.value = {
        success: true,
        message: t('register.success'),
        data: response
      };
      
      // 清空表单
      form.value = {
        name: '',
        phone: '',
        idCard: '',
        password: '',
        confirmPassword: ''
      };
      
      return true;
    } catch (error) {
      registrationResult.value = {
        success: false,
        message: error.detail || t('register.errors.general'),
        errors: error.errors || {}
      };
      
      // 处理后端返回的验证错误
      if (error.errors) {
        errors.value = { ...errors.value, ...error.errors };
      }
      
      return false;
    } finally {
      isLoading.value = false;
    }
  };
  
  // 重置表单
  const resetForm = () => {
    form.value = {
      name: '',
      phone: '',
      idCard: '',
      password: '',
      confirmPassword: ''
    };
    errors.value = {};
    registrationResult.value = null;
  };
  
  // 清除错误
  const clearError = (field) => {
    if (errors.value[field]) {
      delete errors.value[field];
    }
  };
  
  return {
    form,
    errors,
    isLoading,
    registrationResult,
    isFormValid,
    validateForm,
    register,
    resetForm,
    clearError
  };
});