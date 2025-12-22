<template>
  <div class="register-view">
    <div class="register-container">
      <h1>{{ $t('register.title') }}</h1>
      
      <form @submit.prevent="handleSubmit" class="register-form">
        <!-- 姓名 -->
        <div class="form-group">
          <label for="name">{{ $t('register.form.name.label') }}</label>
          <input
            type="text"
            id="name"
            v-model="registerStore.form.name"
            :placeholder="$t('register.form.name.placeholder')"
            @blur="validateField('name')"
            :class="{ 'error': registerStore.errors.name }"
          />
          <span v-if="registerStore.errors.name" class="error-message">
            {{ registerStore.errors.name }}
          </span>
        </div>

        <!-- 手机号 -->
        <div class="form-group">
          <label for="phone">{{ $t('register.form.phone.label') }}</label>
          <input
            type="tel"
            id="phone"
            v-model="registerStore.form.phone"
            :placeholder="$t('register.form.phone.placeholder')"
            @blur="validateField('phone')"
            :class="{ 'error': registerStore.errors.phone }"
          />
          <span v-if="registerStore.errors.phone" class="error-message">
            {{ registerStore.errors.phone }}
          </span>
        </div>

        <!-- 身份证号 -->
        <div class="form-group">
          <label for="idCard">{{ $t('register.form.idCard.label') }}</label>
          <input
            type="text"
            id="idCard"
            v-model="registerStore.form.idCard"
            :placeholder="$t('register.form.idCard.placeholder')"
            @blur="validateField('idCard')"
            :class="{ 'error': registerStore.errors.idCard }"
          />
          <span v-if="registerStore.errors.idCard" class="error-message">
            {{ registerStore.errors.idCard }}
          </span>
        </div>

        <!-- 密码 -->
        <div class="form-group">
          <label for="password">{{ $t('register.form.password.label') }}</label>
          <input
            type="password"
            id="password"
            v-model="registerStore.form.password"
            :placeholder="$t('register.form.password.placeholder')"
            @blur="validateField('password')"
            :class="{ 'error': registerStore.errors.password }"
          />
          <span v-if="registerStore.errors.password" class="error-message">
            {{ registerStore.errors.password }}
          </span>
        </div>

        <!-- 确认密码 -->
        <div class="form-group">
          <label for="confirmPassword">{{ $t('register.form.confirmPassword.label') }}</label>
          <input
            type="password"
            id="confirmPassword"
            v-model="registerStore.form.confirmPassword"
            :placeholder="$t('register.form.confirmPassword.placeholder')"
            @blur="validateField('confirmPassword')"
            :class="{ 'error': registerStore.errors.confirmPassword }"
          />
          <span v-if="registerStore.errors.confirmPassword" class="error-message">
            {{ registerStore.errors.confirmPassword }}
          </span>
        </div>

        <!-- 提交按钮 -->
        <div class="form-actions">
          <button
            type="submit"
            class="submit-btn"
            :disabled="!registerStore.isFormValid || registerStore.isLoading"
          >
            <span v-if="registerStore.isLoading">
              {{ $t('register.submitting') }}
            </span>
            <span v-else>
              {{ $t('register.form.submit') }}
            </span>
          </button>
          
          <button
            type="button"
            class="reset-btn"
            @click="handleReset"
          >
            {{ $t('register.form.reset') }}
          </button>
        </div>
      </form>

      <!-- 注册结果提示 -->
      <div v-if="registerStore.registrationResult" class="result-message" :class="registerStore.registrationResult.success ? 'success' : 'error'">
        {{ registerStore.registrationResult.message }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useRegisterStore } from '../stores/register.js';
import { useI18n } from 'vue-i18n';

const registerStore = useRegisterStore();
const { t } = useI18n();

// 验证单个字段
const validateField = (field) => {
  registerStore.validateForm();
};

// 处理表单提交
const handleSubmit = async () => {
  const success = await registerStore.register();
  if (success) {
    // 注册成功后的处理逻辑
    console.log('Registration successful');
  }
};

// 重置表单
const handleReset = () => {
  registerStore.resetForm();
};

// 组件挂载时的初始化
onMounted(() => {
  // 可以在这里添加初始化逻辑
});
</script>

<style scoped>
.register-view {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f5f5;
  padding: 20px;
}

.register-container {
  background: white;
  padding: 40px;
  border-radius: 10px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
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
  font-weight: 600;
  color: #555;
}

input {
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 16px;
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
  font-size: 14px;
  margin-top: 5px;
}

.form-actions {
  display: flex;
  gap: 15px;
  margin-top: 10px;
}

.submit-btn, .reset-btn {
  padding: 12px 20px;
  border: none;
  border-radius: 5px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
  flex: 1;
}

.submit-btn {
  background-color: #4CAF50;
  color: white;
}

.submit-btn:hover:not(:disabled) {
  background-color: #45a049;
}

.submit-btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.reset-btn {
  background-color: #f44336;
  color: white;
}

.reset-btn:hover {
  background-color: #d32f2f;
}

.result-message {
  margin-top: 20px;
  padding: 15px;
  border-radius: 5px;
  text-align: center;
  font-weight: 600;
}

.result-message.success {
  background-color: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #4CAF50;
}

.result-message.error {
  background-color: #ffebee;
  color: #c62828;
  border: 1px solid #f44336;
}

@media (max-width: 600px) {
  .register-container {
    padding: 20px;
  }
  
  h1 {
    font-size: 24px;
  }
  
  .form-actions {
    flex-direction: column;
  }
}
</style>