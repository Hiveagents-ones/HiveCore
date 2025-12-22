<template>
  <div class="register-view">
    <div class="container">
      <h1>{{ $t('register.title') }}</h1>
      <form @submit.prevent="handleSubmit" class="register-form">
        <div class="form-group">
          <label for="name">{{ $t('register.form.name.label') }}</label>
          <input
            type="text"
            id="name"
            v-model="form.name"
            :placeholder="$t('register.form.name.placeholder')"
            @blur="validateField('name')"
            :class="{ 'is-invalid': errors.name }"
          />
          <span v-if="errors.name" class="error-message">{{ errors.name }}</span>
        </div>

        <div class="form-group">
          <label for="phone">{{ $t('register.form.phone.label') }}</label>
          <input
            type="tel"
            id="phone"
            v-model="form.phone"
            :placeholder="$t('register.form.phone.placeholder')"
            @blur="validateField('phone')"
            :class="{ 'is-invalid': errors.phone }"
          />
          <span v-if="errors.phone" class="error-message">{{ errors.phone }}</span>
        </div>

        <div class="form-group">
          <label for="idCard">{{ $t('register.form.idCard.label') }}</label>
          <input
            type="text"
            id="idCard"
            v-model="form.idCard"
            :placeholder="$t('register.form.idCard.placeholder')"
            @blur="validateField('idCard')"
            :class="{ 'is-invalid': errors.idCard }"
          />
          <span v-if="errors.idCard" class="error-message">{{ errors.idCard }}</span>
        </div>

        <div class="form-group">
          <label for="email">{{ $t('register.form.email.label') }}</label>
          <input
            type="email"
            id="email"
            v-model="form.email"
            :placeholder="$t('register.form.email.placeholder')"
            @blur="validateField('email')"
            :class="{ 'is-invalid': errors.email }"
          />
          <span v-if="errors.email" class="error-message">{{ errors.email }}</span>
        </div>

        <div class="form-actions">
          <button type="submit" :disabled="isSubmitting" class="btn btn-primary">
            {{ isSubmitting ? $t('register.form.submitting') : $t('register.form.submit') }}
          </button>
          <button type="button" @click="resetForm" class="btn btn-secondary">
            {{ $t('register.form.reset') }}
          </button>
        </div>
      </form>

      <!-- Success Modal -->
      <div v-if="showSuccessModal" class="modal-overlay" @click="closeSuccessModal">
        <div class="modal" @click.stop>
          <h2>{{ $t('register.success.title') }}</h2>
          <p>{{ $t('register.success.message', { memberId: registrationResult.member_id }) }}</p>
          <p>{{ $t('register.success.description', { date: formatDate(registrationResult.register_date) }) }}</p>
          <p>{{ $t('register.success.status') }}</p>
          <button @click="closeSuccessModal" class="btn btn-primary">
            {{ $t('register.success.button') }}
          </button>
        </div>
      </div>

      <!-- Error Modal -->
      <div v-if="showErrorModal" class="modal-overlay" @click="closeErrorModal">
        <div class="modal" @click.stop>
          <h2>{{ $t('register.error.title') }}</h2>
          <p>{{ getErrorMessage() }}</p>
          <button @click="closeErrorModal" class="btn btn-primary">
            {{ $t('common.close') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { registerMember } from '@/services/api';

export default {
  name: 'RegisterView',
  setup() {
    const { t } = useI18n();
    const isSubmitting = ref(false);
    const showSuccessModal = ref(false);
    const showErrorModal = ref(false);
    const registrationResult = ref(null);
    const registrationError = ref(null);

    const form = reactive({
      name: '',
      phone: '',
      idCard: '',
      email: ''
    });

    const errors = reactive({
      name: '',
      phone: '',
      idCard: '',
      email: ''
    });

    const validateField = (field) => {
      errors[field] = '';

      switch (field) {
        case 'name':
          if (!form.name.trim()) {
            errors.name = t('register.form.name.required');
          }
          break;
        case 'phone':
          if (!form.phone.trim()) {
            errors.phone = t('register.form.phone.required');
          } else if (!/^1[3-9]\d{9}$/.test(form.phone)) {
            errors.phone = t('register.form.phone.invalid');
          }
          break;
        case 'idCard':
          if (!form.idCard.trim()) {
            errors.idCard = t('register.form.idCard.required');
          } else if (!/(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/.test(form.idCard)) {
            errors.idCard = t('register.form.idCard.invalid');
          }
          break;
        case 'email':
          if (!form.email.trim()) {
            errors.email = t('register.form.email.required');
          } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
            errors.email = t('register.form.email.invalid');
          }
          break;
      }
    };

    const validateForm = () => {
      Object.keys(form).forEach(field => validateField(field));
      return !Object.values(errors).some(error => error);
    };

    const handleSubmit = async () => {
      if (!validateForm()) return;

      isSubmitting.value = true;
      try {
        const result = await registerMember(form);
        registrationResult.value = result;
        showSuccessModal.value = true;
        resetForm();
      } catch (error) {
        registrationError.value = error.message;
        showErrorModal.value = true;
      } finally {
        isSubmitting.value = false;
      }
    };

    const resetForm = () => {
      Object.keys(form).forEach(key => form[key] = '');
      Object.keys(errors).forEach(key => errors[key] = '');
    };

    const closeSuccessModal = () => {
      showSuccessModal.value = false;
      registrationResult.value = null;
    };

    const closeErrorModal = () => {
      showErrorModal.value = false;
      registrationError.value = null;
    };

    const getErrorMessage = () => {
      if (!registrationError.value) return t('register.error.unknown');
      
      if (registrationError.value.includes('already registered')) {
        return t('register.error.duplicate');
      } else if (registrationError.value.includes('network')) {
        return t('register.error.network');
      } else if (registrationError.value.includes('server')) {
        return t('register.error.server');
      }
      return registrationError.value;
    };

    const formatDate = (dateString) => {
      const date = new Date(dateString);
      return date.toLocaleDateString();
    };

    return {
      form,
      errors,
      isSubmitting,
      showSuccessModal,
      showErrorModal,
      registrationResult,
      validateField,
      handleSubmit,
      resetForm,
      closeSuccessModal,
      closeErrorModal,
      getErrorMessage,
      formatDate
    };
  }
};
</script>

<style scoped>
.register-view {
  padding: 2rem 0;
  min-height: 100vh;
  background-color: #f5f5f5;
}

.container {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

h1 {
  text-align: center;
  margin-bottom: 2rem;
  color: #333;
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

label {
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #555;
}

input {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

input:focus {
  outline: none;
  border-color: #4a90e2;
}

input.is-invalid {
  border-color: #e74c3c;
}

.error-message {
  margin-top: 0.25rem;
  color: #e74c3c;
  font-size: 0.875rem;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.3s;
}

.btn-primary {
  background-color: #4a90e2;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #357abd;
}

.btn-primary:disabled {
  background-color: #a0c4e4;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #f0f0f0;
  color: #333;
}

.btn-secondary:hover {
  background-color: #e0e0e0;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  max-width: 500px;
  width: 90%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal h2 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #333;
}

.modal p {
  margin-bottom: 1.5rem;
  color: #555;
}

@media (max-width: 768px) {
  .container {
    margin: 0 1rem;
    padding: 1.5rem;
  }
  
  .form-actions {
    flex-direction: column;
  }
  
  .btn {
    width: 100%;
  }
}
</style>