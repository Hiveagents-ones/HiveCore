import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { registerUser } from '../api/auth';

export const useRegisterStore = defineStore('register', () => {
  // State
  const formData = ref({
    name: '',
    phone: '',
    idCard: '',
    membershipPlan: '',
    paymentMethod: ''
  });

  const isLoading = ref(false);
  const error = ref(null);
  const registrationSuccess = ref(false);

  // Getters
  const isFormValid = computed(() => {
    return (
      formData.value.name.trim() !== '' &&
      formData.value.phone.trim() !== '' &&
      formData.value.idCard.trim() !== '' &&
      formData.value.membershipPlan !== '' &&
      formData.value.paymentMethod !== ''
    );
  });

  // Actions
  const updateFormData = (field, value) => {
    formData.value[field] = value;
  };

  const resetForm = () => {
    formData.value = {
      name: '',
      phone: '',
      idCard: '',
      membershipPlan: '',
      paymentMethod: ''
    };
    error.value = null;
    registrationSuccess.value = false;
  };

  const submitRegistration = async () => {
    if (!isFormValid.value) {
      error.value = '请填写所有必填字段';
      return false;
    }

    isLoading.value = true;
    error.value = null;

    try {
      const response = await registerUser(formData.value);
      if (response.success) {
        registrationSuccess.value = true;
        return true;
      } else {
        error.value = response.message || '注册失败，请重试';
        return false;
      }
    } catch (err) {
      error.value = err.message || '注册过程中发生错误';
      return false;
    } finally {
      isLoading.value = false;
    }
  };

  return {
    // State
    formData,
    isLoading,
    error,
    registrationSuccess,
    // Getters
    isFormValid,
    // Actions
    updateFormData,
    resetForm,
    submitRegistration
  };
});