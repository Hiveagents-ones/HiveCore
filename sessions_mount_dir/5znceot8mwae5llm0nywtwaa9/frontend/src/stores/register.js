import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { registerMember } from '@/services/api';

export const useRegisterStore = defineStore('register', () => {
  const { t } = useI18n();
  
  // Form state
  const form = ref({
    name: '',
    phone: '',
    idCard: '',
    membershipPlan: ''
  });
  
  // UI state
  const isLoading = ref(false);
  const error = ref(null);
  const successMessage = ref('');
  
  // Validation state
  const validationErrors = ref({});
  
  // Computed properties
  const isFormValid = computed(() => {
    return form.value.name && 
           form.value.phone && 
           form.value.idCard && 
           form.value.membershipPlan &&
           Object.keys(validationErrors.value).length === 0;
  });
  
  // Actions
  const validateField = (field, value) => {
    const errors = { ...validationErrors.value };
    
    switch(field) {
      case 'name':
        if (!value || value.trim().length < 2) {
          errors[field] = t('validation.nameRequired');
        } else {
          delete errors[field];
        }
        break;
      case 'phone':
        const phoneRegex = /^1[3-9]\d{9}$/;
        if (!value) {
          errors[field] = t('validation.phoneRequired');
        } else if (!phoneRegex.test(value)) {
          errors[field] = t('validation.phoneInvalid');
        } else {
          delete errors[field];
        }
        break;
      case 'idCard':
        const idCardRegex = /^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[0-9Xx]$/;
        if (!value) {
          errors[field] = t('validation.idCardRequired');
        } else if (!idCardRegex.test(value)) {
          errors[field] = t('validation.idCardInvalid');
        } else {
          delete errors[field];
        }
        break;
      case 'membershipPlan':
        if (!value) {
          errors[field] = t('validation.planRequired');
        } else {
          delete errors[field];
        }
        break;
    }
    
    validationErrors.value = errors;
  };
  
  const updateForm = (field, value) => {
    form.value[field] = value;
    validateField(field, value);
  };
  
  const resetForm = () => {
    form.value = {
      name: '',
      phone: '',
      idCard: '',
      membershipPlan: ''
    };
    validationErrors.value = {};
    error.value = null;
    successMessage.value = '';
  };
  
  const submitForm = async () => {
    // Validate all fields before submission
    Object.keys(form.value).forEach(field => {
      validateField(field, form.value[field]);
    });
    
    if (!isFormValid.value) {
      error.value = t('validation.formInvalid');
      return false;
    }
    
    isLoading.value = true;
    error.value = null;
    successMessage.value = '';
    
    try {
      const response = await registerMember(form.value);
      
      if (response.success) {
        successMessage.value = t('register.success');
        resetForm();
        return true;
      } else {
        // Handle API validation errors
        if (response.errors) {
          validationErrors.value = response.errors;
        }
        error.value = response.message || t('register.failed');
        return false;
      }
    } catch (err) {
      // Map different error types to user-friendly messages
      if (err.response?.status === 409) {
        error.value = t('register.duplicate');
      } else if (err.response?.status === 400) {
        error.value = t('register.invalidData');
      } else if (err.response?.status === 500) {
        error.value = t('register.serverError');
      } else {
        error.value = t('register.networkError');
      }
      return false;
    } finally {
      isLoading.value = false;
    }
  };
  
  return {
    // State
    form,
    isLoading,
    error,
    successMessage,
    validationErrors,
    
    // Computed
    isFormValid,
    
    // Actions
    updateForm,
    resetForm,
    submitForm,
    validateField
  };
});