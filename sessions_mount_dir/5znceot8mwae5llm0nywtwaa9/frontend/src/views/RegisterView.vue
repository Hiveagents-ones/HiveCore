<template>
  <div class="register-view">
    <div class="register-container">
      <h1>{{ $t('register.title') }}</h1>
      
      <form @submit.prevent="handleSubmit" class="register-form">
        <!-- Name Field -->
        <div class="form-group">
          <label for="name">{{ $t('register.form.name.label') }} *</label>
          <input
            id="name"
            v-model="registerStore.form.name"
            @blur="validateField('name')"
            :placeholder="$t('register.form.name.placeholder')"
            :class="{ 'error': registerStore.validationErrors.name }"
            type="text"
            required
          />
          <span v-if="registerStore.validationErrors.name" class="error-message">
            {{ registerStore.validationErrors.name }}
          </span>
        </div>

        <!-- Phone Field -->
        <div class="form-group">
          <label for="phone">{{ $t('register.form.phone.label') }} *</label>
          <input
            id="phone"
            v-model="registerStore.form.phone"
            @blur="validateField('phone')"
            :placeholder="$t('register.form.phone.placeholder')"
            :class="{ 'error': registerStore.validationErrors.phone }"
            type="tel"
            required
          />
          <span v-if="registerStore.validationErrors.phone" class="error-message">
            {{ registerStore.validationErrors.phone }}
          </span>
        </div>

        <!-- ID Card Field -->
        <div class="form-group">
          <label for="idCard">{{ $t('register.form.idCard.label') }} *</label>
          <input
            id="idCard"
            v-model="registerStore.form.idCard"
            @blur="validateField('idCard')"
            :placeholder="$t('register.form.idCard.placeholder')"
            :class="{ 'error': registerStore.validationErrors.idCard }"
            type="text"
            required
          />
          <span v-if="registerStore.validationErrors.idCard" class="error-message">
            {{ registerStore.validationErrors.idCard }}
          </span>
        </div>

        <!-- Membership Plan Field -->
        <div class="form-group">
          <label for="membershipPlan">{{ $t('register.form.membershipPlan.label') }} *</label>
          <select
            id="membershipPlan"
            v-model="registerStore.form.membershipPlan"
            @blur="validateField('membershipPlan')"
            :class="{ 'error': registerStore.validationErrors.membershipPlan }"
            required
          >
            <option value="">{{ $t('register.form.membershipPlan.placeholder') }}</option>
            <option value="basic">{{ $t('register.form.membershipPlan.options.basic') }}</option>
            <option value="standard">{{ $t('register.form.membershipPlan.options.standard') }}</option>
            <option value="premium">{{ $t('register.form.membershipPlan.options.premium') }}</option>
          </select>
          <span v-if="registerStore.validationErrors.membershipPlan" class="error-message">
            {{ registerStore.validationErrors.membershipPlan }}
          </span>
        </div>

        <!-- Privacy Policy Checkbox -->
        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input
              v-model="agreeToPrivacy"
              type="checkbox"
              required
            />
            <span>{{ $t('register.form.privacyPolicy.label') }}</span>
            <a href="#" @click.prevent="showPrivacyPolicy">{{ $t('register.form.privacyPolicy.link') }}</a>
          </label>
          <span v-if="privacyError" class="error-message">
            {{ privacyError }}
          </span>
        </div>

        <!-- Form Actions -->
        <div class="form-actions">
          <button
            type="submit"
            :disabled="!canSubmit"
            class="btn btn-primary"
          >
            <span v-if="registerStore.isLoading">{{ $t('register.messages.loading') }}</span>
            <span v-else>{{ $t('register.form.submit') }}</span>
          </button>
          <button
            type="button"
            @click="handleReset"
            :disabled="registerStore.isLoading"
            class="btn btn-secondary"
          >
            {{ $t('register.form.reset') }}
          </button>
        </div>

        <!-- Messages -->
        <div v-if="registerStore.error" class="message error">
          {{ registerStore.error }}
        </div>
        <div v-if="registerStore.successMessage" class="message success">
          {{ registerStore.successMessage }}
        </div>
      </form>
    </div>

    <!-- Privacy Policy Modal -->
    <div v-if="showPrivacyModal" class="modal-overlay" @click="closePrivacyPolicy">
      <div class="modal-content" @click.stop>
        <h2>{{ $t('register.form.privacyPolicy.title') }}</h2>
        <div class="privacy-content">
          <p>{{ $t('register.form.privacyPolicy.content') }}</p>
        </div>
        <button @click="closePrivacyPolicy" class="btn btn-primary">
          {{ $t('register.form.privacyPolicy.close') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useRegisterStore } from '@/stores/register';
import { useI18n } from 'vue-i18n';

const registerStore = useRegisterStore();
const { t } = useI18n();

const agreeToPrivacy = ref(false);
const privacyError = ref('');
const showPrivacyModal = ref(false);

const canSubmit = computed(() => {
  return registerStore.isFormValid && 
         agreeToPrivacy.value && 
         !registerStore.isLoading;
});

const validateField = (field) => {
  registerStore.validateField(field, registerStore.form[field]);
};

const validatePrivacy = () => {
  if (!agreeToPrivacy.value) {
    privacyError.value = t('validation.privacyRequired');
    return false;
  }
  privacyError.value = '';
  return true;
};

const handleSubmit = async () => {
  if (!validatePrivacy()) {
    return;
  }

  await registerStore.submitForm();
};

const handleReset = () => {
  registerStore.resetForm();
  agreeToPrivacy.value = false;
  privacyError.value = '';
};

const showPrivacyPolicy = () => {
  showPrivacyModal.value = true;
};

const closePrivacyPolicy = () => {
  showPrivacyModal.value = false;
};
</script>

<style scoped>
.register-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.register-container {
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 500px;
}

h1 {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
  font-size: 28px;
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
}

label {
  margin-bottom: 8px;
  color: #555;
  font-weight: 500;
}

input, select {
  padding: 12px;
  border: 2px solid #e1e5e9;
  border-radius: 8px;
  font-size: 16px;
  transition: all 0.3s ease;
}

input:focus, select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

input.error, select.error {
  border-color: #e74c3c;
}

.error-message {
  color: #e74c3c;
  font-size: 14px;
  margin-top: 5px;
}

.checkbox-group {
  flex-direction: row;
  align-items: flex-start;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: normal;
}

.checkbox-label input[type="checkbox"] {
  width: auto;
  margin: 0;
}

.checkbox-label a {
  color: #667eea;
  text-decoration: none;
}

.checkbox-label a:hover {
  text-decoration: underline;
}

.form-actions {
  display: flex;
  gap: 15px;
  margin-top: 10px;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  flex: 1;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5a67d8;
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}

.btn-secondary {
  background: #e1e5e9;
  color: #555;
}

.btn-secondary:hover:not(:disabled) {
  background: #d1d5d9;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.message {
  padding: 12px;
  border-radius: 8px;
  text-align: center;
  font-weight: 500;
}

.message.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.message.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 30px;
  border-radius: 12px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-content h2 {
  margin-bottom: 20px;
  color: #333;
}

.privacy-content {
  margin-bottom: 20px;
  line-height: 1.6;
  color: #555;
}

@media (max-width: 600px) {
  .register-container {
    padding: 30px 20px;
  }
  
  .form-actions {
    flex-direction: column;
  }
}
</style>