<template>
  <div class="register-container">
    <div class="register-form">
      <h2>{{ $t('auth.register.title') }}</h2>
      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label for="username">{{ $t('auth.register.username') }}</label>
          <input
            type="text"
            id="username"
            v-model="formData.username"
            :class="{ 'error': errors.username }"
            @blur="validateUsername"
          />
          <span class="error-message" v-if="errors.username">{{ errors.username }}</span>
        </div>
        
        <div class="form-group">
          <label for="password">{{ $t('auth.register.password') }}</label>
          <input
            type="password"
            id="password"
            v-model="formData.password"
            :class="{ 'error': errors.password }"
            @blur="validatePassword"
          />
          <span class="error-message" v-if="errors.password">{{ errors.password }}</span>
        </div>
        
        <div class="form-group">
          <label for="confirmPassword">{{ $t('auth.register.confirmPassword') }}</label>
          <input
            type="password"
            id="confirmPassword"
            v-model="formData.confirmPassword"
            :class="{ 'error': errors.confirmPassword }"
            @blur="validateConfirmPassword"
          />
          <span class="error-message" v-if="errors.confirmPassword">{{ errors.confirmPassword }}</span>
        </div>
        
        <button type="submit" :disabled="isSubmitting" class="submit-btn">
          {{ isSubmitting ? 'Registering...' : $t('auth.register.submit') }}
        </button>
        
        <div class="message" :class="messageType" v-if="message">
          {{ message }}
        </div>
      </form>
    </div>
  </div>
</template>

<script>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { register } from '@/api/member';

export default {
  name: 'Register',
  setup() {
    const router = useRouter();
    const { t } = useI18n();
    
    const formData = reactive({
      username: '',
      password: '',
      confirmPassword: ''
    });
    
    const errors = reactive({
      username: '',
      password: '',
      confirmPassword: ''
    });
    
    const isSubmitting = ref(false);
    const message = ref('');
    const messageType = ref('');
    
    const validateUsername = () => {
      if (!formData.username) {
        errors.username = t('auth.register.usernameRequired');
        return false;
      }
      errors.username = '';
      return true;
    };
    
    const validatePassword = () => {
      if (!formData.password) {
        errors.password = t('auth.register.passwordRequired');
        return false;
      }
      if (formData.password.length < 6) {
        errors.password = t('auth.register.passwordMinLength');
        return false;
      }
      errors.password = '';
      return true;
    };
    
    const validateConfirmPassword = () => {
      if (!formData.confirmPassword) {
        errors.confirmPassword = t('auth.register.passwordRequired');
        return false;
      }
      if (formData.password !== formData.confirmPassword) {
        errors.confirmPassword = t('auth.register.passwordMismatch');
        return false;
      }
      errors.confirmPassword = '';
      return true;
    };
    
    const validateForm = () => {
      const isUsernameValid = validateUsername();
      const isPasswordValid = validatePassword();
      const isConfirmPasswordValid = validateConfirmPassword();
      return isUsernameValid && isPasswordValid && isConfirmPasswordValid;
    };
    
    const handleRegister = async () => {
      if (!validateForm()) {
        return;
      }
      
      isSubmitting.value = true;
      message.value = '';
      
      try {
        await register({
          username: formData.username,
          password: formData.password
        });
        
        message.value = t('auth.register.registerSuccess');
        messageType.value = 'success';
        
        setTimeout(() => {
          router.push('/login');
        }, 1500);
      } catch (error) {
        if (error.detail === 'Username already registered') {
          errors.username = t('auth.register.usernameExists');
        } else {
          message.value = t('auth.register.registerFailed');
          messageType.value = 'error';
        }
      } finally {
        isSubmitting.value = false;
      }
    };
    
    return {
      formData,
      errors,
      isSubmitting,
      message,
      messageType,
      validateUsername,
      validatePassword,
      validateConfirmPassword,
      handleRegister
    };
  }
};
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f5f5;
}

.register-form {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
}

h2 {
  text-align: center;
  margin-bottom: 1.5rem;
  color: #333;
}

.form-group {
  margin-bottom: 1rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  color: #555;
  font-weight: 500;
}

input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

input:focus {
  outline: none;
  border-color: #4CAF50;
}

input.error {
  border-color: #f44336;
}

.error-message {
  color: #f44336;
  font-size: 0.875rem;
  margin-top: 0.25rem;
  display: block;
}

.submit-btn {
  width: 100%;
  padding: 0.75rem;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.3s;
}

.submit-btn:hover:not(:disabled) {
  background-color: #45a049;
}

.submit-btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.message {
  margin-top: 1rem;
  padding: 0.75rem;
  border-radius: 4px;
  text-align: center;
}

.message.success {
  background-color: #dff0d8;
  color: #3c763d;
}

.message.error {
  background-color: #f2dede;
  color: #a94442;
}
</style>